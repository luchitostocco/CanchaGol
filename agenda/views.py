from datetime import datetime, time, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from . import services
from .forms import (
    BloqueoForm, CanchaForm, DisponibilidadForm, FiltroAgendaForm,
    MotivoForm, PrecioForm, PublicarForm, RegistroForm,
)
from .models import Cancha, Reserva, Turno, Usuario


def rol_requerido(rol):
    def decorar(vista):
        @login_required
        @wraps(vista)
        def autorizada(request, *args, **kwargs):
            services.exigir_rol(request.user, rol)
            return vista(request, *args, **kwargs)
        return autorizada
    return decorar


cliente = rol_requerido(Usuario.Rol.CLIENTE)
admin = rol_requerido(Usuario.Rol.ADMIN)


def _dia(fecha):
    inicio = timezone.make_aware(datetime.combine(fecha, time.min))
    return inicio, inicio + timedelta(days=1)


@require_safe
def inicio(request):
    hoy = timezone.localdate()
    form = DisponibilidadForm(request.GET or {"modalidad": "F5", "fecha": hoy.isoformat()})
    turnos = Turno.objects.none()
    if form.is_valid():
        comienzo, fin = _dia(form.cleaned_data["fecha"])
        ocupada = Reserva.objects.filter(turno_ocupado=OuterRef("pk"))
        turnos = Turno.objects.select_related("cancha__tipo").filter(
            ~Exists(ocupada),
            cancha__activa=True,
            cancha__tipo__codigo=form.cleaned_data["modalidad"],
            habilitado=True,
            inicio__gte=comienzo,
            inicio__lt=fin,
            inicio__gt=timezone.now(),
        )
    return render(request, "agenda/inicio.html", {"form": form, "turnos": turnos})


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = RegistroForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            usuario = form.save()
        except IntegrityError:
            if not Usuario.objects.filter(email=form.cleaned_data["email"]).exists():
                raise
            form.add_error("email", "Ya hay una cuenta con ese correo.")
        else:
            login(request, usuario)
            messages.success(request, "Tu cuenta ya está lista.")
            return redirect("inicio")
    return render(request, "agenda/formulario.html", {
        "titulo": "Crear cuenta", "form": form, "accion": "Registrarme", "volver": "inicio",
    })


@cliente
def reservar(request, turno_id):
    turno = get_object_or_404(Turno.objects.select_related("cancha__tipo"), pk=turno_id)
    disponibilidad = reverse("inicio", query={
        "modalidad": turno.cancha.tipo.codigo, "fecha": timezone.localtime(turno.inicio).date(),
    })
    if request.method == "POST":
        form = PrecioForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Revisá el precio antes de confirmar.")
            return redirect("reservar", turno_id=turno_id)
        try:
            reserva = services.confirmar(request.user, turno_id, form.cleaned_data["precio"])
        except ValidationError as error:
            messages.error(request, error.messages[0])
            if error.code == "precio_cambio":
                return redirect("reservar", turno_id=turno_id)
            return redirect(disponibilidad)
        messages.success(request, f"Reserva #{reserva.pk} confirmada por $ {reserva.importe_acordado:.2f} ARS.")
        return redirect("mis_reservas")
    if not services.turno_libre(turno.cancha, turno, timezone.now()):
        messages.error(request, "Este turno ya no está disponible.")
        return redirect(disponibilidad)
    return render(request, "agenda/reservar.html", {"turno": turno, "disponibilidad": disponibilidad})


@cliente
@require_safe
def mis_reservas(request):
    ahora = timezone.now()
    reservas = list(Reserva.objects.filter(cliente=request.user).select_related("turno__cancha__tipo"))
    for reserva in reservas:
        reserva.cancelable = reserva.puede_cancelarse(ahora)
    return render(request, "agenda/mis_reservas.html", {"reservas": reservas})


@cliente
@require_POST
def cancelar(request, reserva_id):
    return _accion(request, lambda: services.cancelar_propia(request.user, reserva_id),
                   "Reserva cancelada. El horario vuelve a estar disponible si sigue habilitado.", "mis_reservas")


def _accion(request, guardar, aviso, destino="gestion"):
    try:
        guardar()
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, aviso)
    return redirect(destino)


@admin
@require_safe
def gestion(request):
    form = FiltroAgendaForm(request.GET if request.GET else {"fecha": timezone.localdate().isoformat()})
    canchas = Cancha.objects.select_related("tipo")
    turnos = Turno.objects.select_related("cancha__tipo")
    reservas = Reserva.objects.select_related("turno__cancha", "cliente")
    if form.is_valid():
        filtros = form.cleaned_data
        if filtros["fecha"]:
            inicio, fin = _dia(filtros["fecha"])
            turnos = turnos.filter(inicio__gte=inicio, inicio__lt=fin)
        if filtros["cancha"]:
            turnos = turnos.filter(cancha=filtros["cancha"])
        reservas = reservas.filter(turno__in=turnos)
        if filtros["estado"]:
            reservas = reservas.filter(estado=filtros["estado"])
    else:
        turnos = turnos.none()
        reservas = reservas.none()
    return render(request, "agenda/gestion.html", {
        "form": form, "canchas": canchas, "turnos": turnos, "reservas": reservas, "ahora": timezone.now(),
    })


def _formulario(request, form, guardar, titulo, aviso, detalle=None, accion="Guardar"):
    if request.method == "POST" and form.is_valid():
        try:
            guardar(form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, aviso)
            return redirect("gestion")
    return render(request, "agenda/formulario.html", {
        "form": form, "titulo": titulo, "detalle": detalle, "accion": accion, "volver": "gestion",
    })


def _datos(request):
    return request.POST if request.method == "POST" else None


@admin
def editar_cancha(request, cancha_id=None):
    cancha = get_object_or_404(Cancha, pk=cancha_id) if cancha_id else None
    form = CanchaForm(_datos(request), instance=cancha)

    def guardar(datos):
        try:
            if cancha_id:
                services.cambiar_cancha(cancha_id, datos)
            else:
                form.save()
        except IntegrityError:
            if Cancha.objects.filter(nombre=datos["nombre"]).exclude(pk=cancha_id).exists():
                raise ValidationError("Ya existe una cancha con ese nombre.")
            raise

    return _formulario(request, form, guardar, "Editar cancha" if cancha_id else "Nueva cancha", "Cancha guardada.")


@admin
def nuevo_turno(request):
    return _formulario(
        request, PublicarForm(_datos(request)),
        lambda d: services.publicar_turno(d["cancha"].pk, d["inicio"], d["precio"]),
        "Publicar turno", "Turno publicado.", "Cada turno dura 60 minutos. La hora corresponde a Buenos Aires.",
        accion="Publicar turno",
    )


@admin
def precio(request, turno_id):
    turno = get_object_or_404(Turno.objects.select_related("cancha"), pk=turno_id)
    return _formulario(
        request, PrecioForm(_datos(request), initial={"precio": turno.precio}),
        lambda d: services.actualizar_precio(turno_id, d["precio"]),
        "Cambiar precio", "Precio actualizado.", turno.cancha.nombre,
    )


@admin
def bloquear(request, turno_id):
    turno = get_object_or_404(Turno.objects.select_related("cancha"), pk=turno_id)
    return _formulario(
        request, BloqueoForm(_datos(request)),
        lambda d: services.cambiar_bloqueo(turno_id, d["motivo"], d["cancelar_reserva"]),
        "Bloquear turno", "Turno bloqueado.", turno.cancha.nombre, accion="Bloquear turno",
    )


@admin
@require_POST
def habilitar(request, turno_id):
    return _accion(request, lambda: services.cambiar_bloqueo(turno_id, None), "Turno habilitado.")


@admin
def cancelar_admin(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    return _formulario(
        request, MotivoForm(_datos(request)), lambda d: services.gestionar_reserva(reserva_id, d["motivo"]),
        f"Cancelar reserva #{reserva.pk}", "Reserva cancelada.", accion="Cancelar reserva",
    )


@admin
@require_POST
def completar(request, reserva_id):
    return _accion(request, lambda: services.gestionar_reserva(reserva_id), "Reserva completada.")
