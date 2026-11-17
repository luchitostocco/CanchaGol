from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Cancha, Reserva, Turno, Usuario


def exigir_rol(usuario, rol):
    if not usuario.is_active or usuario.rol != rol:
        raise PermissionDenied


def _bloquear_turno(turno_id):
    # Todas las escrituras de agenda toman primero el bloqueo de la cancha.
    turno = get_object_or_404(Turno.objects.only("cancha_id"), pk=turno_id)
    cancha = get_object_or_404(Cancha.objects.select_for_update(), pk=turno.cancha_id)
    turno = get_object_or_404(Turno.objects.select_for_update(), pk=turno_id)
    return cancha, turno


def turno_libre(cancha, turno, ahora):
    return (
        cancha.activa
        and turno.habilitado
        and turno.inicio > ahora
        and not Reserva.objects.filter(turno_ocupado=turno.pk).exists()
    )


@transaction.atomic
def confirmar(usuario, turno_id, precio_revisado):
    exigir_rol(usuario, Usuario.Rol.CLIENTE)
    cancha, turno = _bloquear_turno(turno_id)
    if not turno_libre(cancha, turno, timezone.now()):
        raise ValidationError("Este turno ya no está disponible.")
    if turno.precio != precio_revisado:
        raise ValidationError("El precio cambió. Revisá el nuevo importe antes de confirmar.", code="precio_cambio")
    try:
        with transaction.atomic():
            return Reserva.objects.create(cliente=usuario, turno=turno, importe_acordado=turno.precio)
    except IntegrityError:
        if Reserva.objects.filter(turno_ocupado=turno.pk).exists():
            raise ValidationError("Este turno ya no está disponible.")
        raise


def _cancelar(reserva, motivo, ahora):
    reserva.estado = Reserva.Estado.CANCELADA
    reserva.cancelada_en = ahora
    reserva.motivo_cancelacion = motivo
    reserva.save(update_fields=["estado", "cancelada_en", "motivo_cancelacion"])


@transaction.atomic
def cancelar_propia(usuario, reserva_id):
    exigir_rol(usuario, Usuario.Rol.CLIENTE)
    original = get_object_or_404(Reserva, pk=reserva_id, cliente=usuario)
    _, turno = _bloquear_turno(original.turno_id)
    reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
    reserva.turno = turno
    ahora = timezone.now()
    if not reserva.puede_cancelarse(ahora):
        raise ValidationError("Solo podés cancelar una reserva confirmada con al menos 24 horas de anticipación.")
    _cancelar(reserva, "Cancelada por el cliente", ahora)


@transaction.atomic
def publicar_turno(cancha_id, inicio, precio):
    cancha = get_object_or_404(Cancha.objects.select_for_update(), pk=cancha_id)
    if not cancha.activa:
        raise ValidationError("La cancha está desactivada.")
    if inicio <= timezone.now():
        raise ValidationError("Elegí una fecha y hora futura.")
    fin = inicio + timedelta(hours=1)
    if Turno.objects.filter(cancha=cancha, inicio__lt=fin, fin__gt=inicio).exists():
        raise ValidationError("El horario se superpone con otro turno de esa cancha.")
    return Turno.objects.create(cancha=cancha, inicio=inicio, fin=fin, precio=precio)


@transaction.atomic
def actualizar_precio(turno_id, precio):
    _, turno = _bloquear_turno(turno_id)
    if turno.inicio <= timezone.now():
        raise ValidationError("Solo se puede cambiar el precio de un turno futuro.")
    turno.precio = precio
    turno.save(update_fields=["precio"])


@transaction.atomic
def cambiar_bloqueo(turno_id, motivo, cancelar_reserva=False):
    cancha, turno = _bloquear_turno(turno_id)
    ahora = timezone.now()
    if turno.inicio <= ahora:
        raise ValidationError("Solo se pueden cambiar los bloqueos de turnos futuros.")
    if motivo:
        reserva = Reserva.objects.select_for_update().filter(turno_ocupado=turno.pk).first()
        if reserva:
            if reserva.estado != Reserva.Estado.CONFIRMADA or not cancelar_reserva:
                raise ValidationError("Para bloquear este turno, autorizá la cancelación de la reserva e indicá el motivo.")
            _cancelar(reserva, motivo, ahora)
    elif not cancha.activa:
        raise ValidationError("Activá la cancha antes de habilitar el turno.")
    turno.habilitado = not motivo
    turno.motivo_bloqueo = motivo or None
    turno.save(update_fields=["habilitado", "motivo_bloqueo"])


@transaction.atomic
def cambiar_cancha(cancha_id, datos):
    cancha = get_object_or_404(Cancha.objects.select_for_update(), pk=cancha_id)
    if not datos["activa"] and Reserva.objects.filter(
        turno__cancha=cancha,
        turno__inicio__gt=timezone.now(),
        estado=Reserva.Estado.CONFIRMADA,
    ).exists():
        raise ValidationError("Resolvé las reservas futuras confirmadas antes de desactivar la cancha.")
    for campo, valor in datos.items():
        setattr(cancha, campo, valor)
    cancha.save(update_fields=list(datos))


@transaction.atomic
def gestionar_reserva(reserva_id, motivo=None):
    original = get_object_or_404(Reserva, pk=reserva_id)
    _, turno = _bloquear_turno(original.turno_id)
    reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
    ahora = timezone.now()
    if reserva.estado != Reserva.Estado.CONFIRMADA:
        raise ValidationError("La reserva ya tiene un estado final.")
    if motivo:
        _cancelar(reserva, motivo, ahora)
    else:
        if turno.fin > ahora:
            raise ValidationError("El turno todavía no finalizó.")
        reserva.estado = Reserva.Estado.COMPLETADA
        reserva.save(update_fields=["estado"])
