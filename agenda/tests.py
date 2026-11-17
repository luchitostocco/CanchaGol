from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from decimal import Decimal
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import Cancha, Reserva, TipoCancha, Turno, Usuario


def crear_turno(dias=2):
    cancha = Cancha.objects.create(nombre="Cancha Norte", tipo=TipoCancha.objects.get(codigo="F5"))
    fecha = timezone.localdate() + timedelta(days=dias)
    inicio = timezone.make_aware(datetime.combine(fecha, time(19)))
    return Turno.objects.create(cancha=cancha, inicio=inicio, fin=inicio + timedelta(hours=1), precio=12000)


class ReservaGolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.turno = crear_turno()
        cls.cliente = Usuario.objects.create_user("cliente@example.com", "Cliente")
        cls.otro = Usuario.objects.create_user("otro@example.com", "Otro")
        cls.admin = Usuario.objects.create_superuser("admin@example.com", "Administrador")

    def confirmar(self):
        return services.confirmar(self.cliente, self.turno.pk, self.turno.precio)

    def disponibilidad(self, turno, modalidad="F5"):
        return self.client.get(reverse("inicio"), {
            "modalidad": modalidad, "fecha": timezone.localtime(turno.inicio).date(),
        }).context["turnos"]

    def test_registro_e_ingreso_por_correo(self):
        datos = {
            "nombre": "Lucía", "email": "LUCIA@EXAMPLE.COM", "telefono": "",
            "password1": "Muy-fuerte-74-Z", "password2": "Muy-fuerte-74-Z",
        }
        self.assertRedirects(self.client.post(reverse("registro"), datos), reverse("inicio"))
        cuenta = Usuario.objects.get(email="lucia@example.com")
        self.assertEqual(cuenta.rol, Usuario.Rol.CLIENTE)
        self.assertTrue(cuenta.check_password(datos["password1"]))
        self.assertRedirects(self.client.post(reverse("salir")), reverse("inicio"))
        response = self.client.post(reverse("ingresar"), {
            "username": "LUCIA@EXAMPLE.COM", "password": datos["password1"],
        })
        self.assertRedirects(response, reverse("inicio"))

    def test_hu01_confirmar_mostrar_cancelar_y_volver_a_ofrecer(self):
        self.client.force_login(self.cliente)
        self.assertEqual(list(self.disponibilidad(self.turno)), [self.turno])
        self.assertFalse(self.disponibilidad(self.turno, "F7").exists())
        enlace = reverse("reservar", args=[self.turno.pk])
        self.assertContains(self.client.get(enlace), "Confirmar reserva")
        self.assertRedirects(self.client.post(enlace, {"precio": 12000}), reverse("mis_reservas"))
        reserva = Reserva.objects.get()
        self.assertContains(self.client.get(reverse("mis_reservas")), f"Reserva #{reserva.pk}")
        self.assertEqual(reserva.importe_acordado, Decimal("12000.00"))
        self.assertFalse(self.disponibilidad(self.turno).exists())
        self.assertRedirects(self.client.post(reverse("cancelar", args=[reserva.pk])), reverse("mis_reservas"))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.CANCELADA)
        self.assertIsNone(reserva.turno_ocupado)
        self.assertEqual(list(self.disponibilidad(self.turno)), [self.turno])
        otra = services.confirmar(self.otro, self.turno.pk, self.turno.precio)
        self.assertNotEqual(otra.pk, reserva.pk)

    def test_hu01_unicidad_en_base_y_rechazo_de_segunda_confirmacion(self):
        self.confirmar()
        with self.assertRaisesMessage(ValidationError, "ya no está disponible"):
            services.confirmar(self.otro, self.turno.pk, self.turno.precio)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reserva.objects.create(
                cliente=self.otro, turno=self.turno, importe_acordado=12000, estado=Reserva.Estado.COMPLETADA,
            )
        self.assertEqual(Reserva.objects.count(), 1)

    def test_hu01_cancela_solo_el_titular_con_24_horas_o_mas(self):
        reserva = self.confirmar()
        self.client.force_login(self.otro)
        self.assertEqual(self.client.post(reverse("cancelar", args=[reserva.pk])).status_code, 404)
        self.assertFalse(self.client.get(reverse("mis_reservas")).context["reservas"])
        limite = self.turno.inicio - timedelta(hours=24)
        reserva.turno = self.turno
        self.assertTrue(reserva.puede_cancelarse(limite))
        self.assertFalse(reserva.puede_cancelarse(limite + timedelta(seconds=1)))
        from unittest.mock import patch
        with patch("agenda.services.timezone.now", return_value=limite + timedelta(seconds=1)):
            with self.assertRaisesMessage(ValidationError, "24 horas"):
                services.cancelar_propia(self.cliente, reserva.pk)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.CONFIRMADA)

    def test_hu01_precio_modificado_antes_de_confirmar(self):
        self.client.force_login(self.cliente)
        services.actualizar_precio(self.turno.pk, Decimal("13000"))
        enlace = reverse("reservar", args=[self.turno.pk])
        self.assertContains(self.client.post(enlace, {"precio": 12000}, follow=True), "El precio cambió.")
        self.assertFalse(Reserva.objects.exists())

    def test_hu01_excluye_turnos_pasados_bloqueados_y_canchas_inactivas(self):
        self.assertFalse(self.disponibilidad(crear_turno_pasado(self.turno.cancha)).exists())
        services.cambiar_bloqueo(self.turno.pk, "Mantenimiento")
        self.assertFalse(self.disponibilidad(self.turno).exists())
        services.cambiar_bloqueo(self.turno.pk, None)
        Cancha.objects.filter(pk=self.turno.cancha_id).update(activa=False)
        self.assertFalse(self.disponibilidad(self.turno).exists())

    def test_hu02_publicacion_y_superposicion(self):
        self.client.force_login(self.admin)
        url = reverse("nuevo_turno")
        datos = {"cancha": self.turno.cancha_id, "precio": 8000}
        cruce = timezone.localtime(self.turno.inicio) + timedelta(minutes=30)
        self.assertContains(self.client.post(url, datos | {"inicio": cruce.isoformat()}), "se superpone")
        siguiente = timezone.localtime(self.turno.fin)
        self.assertRedirects(self.client.post(url, datos | {"inicio": siguiente.isoformat()}), reverse("gestion"))
        nuevo = Turno.objects.get(inicio=siguiente)
        self.assertEqual(nuevo.fin - nuevo.inicio, timedelta(hours=1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Turno.objects.filter(pk=nuevo.pk).update(fin=nuevo.inicio + timedelta(minutes=59))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Turno.objects.filter(pk=nuevo.pk).update(precio=-1)

    def test_hu02_bloqueo_atomico_precio_historico_y_baja_logica(self):
        reserva = self.confirmar()
        cancha = self.turno.cancha
        self.client.force_login(self.admin)
        editar = reverse("editar_cancha", args=[cancha.pk])
        datos_cancha = {"nombre": cancha.nombre, "tipo": cancha.tipo_id}
        self.assertContains(self.client.post(editar, datos_cancha), "Resolvé las reservas futuras")
        self.client.post(reverse("precio", args=[self.turno.pk]), {"precio": 19000})
        bloqueo = reverse("bloquear", args=[self.turno.pk])
        self.assertContains(self.client.post(bloqueo, {"motivo": "Lluvia"}), "autorizá la cancelación")
        self.turno.refresh_from_db()
        self.assertTrue(self.turno.habilitado)
        self.assertRedirects(
            self.client.post(bloqueo, {"motivo": "Lluvia", "cancelar_reserva": "on"}), reverse("gestion"),
        )
        reserva.refresh_from_db()
        self.turno.refresh_from_db()
        self.assertEqual(self.turno.motivo_bloqueo, "Lluvia")
        self.assertFalse(self.turno.habilitado)
        self.assertEqual(reserva.motivo_cancelacion, "Lluvia")
        self.assertEqual(reserva.estado, Reserva.Estado.CANCELADA)
        self.assertEqual(reserva.importe_acordado, Decimal("12000"))
        self.assertEqual(self.turno.precio, Decimal("19000"))
        self.assertRedirects(self.client.post(editar, datos_cancha), reverse("gestion"))
        cancha.refresh_from_db()
        self.assertFalse(cancha.activa)

    def test_hu02_filtro_cierre_y_permisos(self):
        reserva = self.confirmar()
        url = reverse("completar", args=[reserva.pk])
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse("gestion")).status_code, 403)
        self.assertEqual(self.client.post(reverse("precio", args=[self.turno.pk]), {"precio": 0}).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.post(url, follow=True), "todavía no finalizó")
        pasado = crear_turno_pasado(self.turno.cancha)
        reserva_pasada = Reserva.objects.create(cliente=self.cliente, turno=pasado, importe_acordado=12000)
        self.assertRedirects(self.client.post(reverse("completar", args=[reserva_pasada.pk])), reverse("gestion"))
        response = self.client.get(reverse("gestion"), {
            "fecha": timezone.localtime(pasado.inicio).date(), "cancha": self.turno.cancha_id, "estado": "COMPLETADA",
        })
        self.assertEqual(list(response.context["reservas"]), [reserva_pasada])


def crear_turno_pasado(cancha):
    inicio = timezone.now() - timedelta(days=1, hours=2)
    return Turno.objects.create(cancha=cancha, inicio=inicio, fin=inicio + timedelta(hours=1), precio=12000)


class ConcurrenciaTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_solo_una_confirmacion_simultanea_tiene_exito(self):
        TipoCancha.objects.get_or_create(codigo="F5")
        turno = crear_turno()
        personas = [
            Usuario.objects.create_user(f"cliente{i}@example.com", f"Cliente {i}") for i in range(2)
        ]
        listos = Barrier(2, timeout=10)

        def confirmar(usuario):
            try:
                listos.wait()
                services.confirmar(usuario, turno.pk, Decimal("12000"))
                return "confirmada"
            except ValidationError as error:
                return error.messages[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            resultados = list(workers.map(confirmar, personas))
        self.assertCountEqual(resultados, ["confirmada", "Este turno ya no está disponible."])
        self.assertEqual(Reserva.objects.count(), 1)
