from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from agenda.models import Cancha, TipoCancha, Turno
from agenda.services import publicar_turno


class Command(BaseCommand):
    help = "Agrega canchas y turnos de demostración para fechas próximas."

    def handle(self, *args, **options):
        canchas = [
            ("La Cinco", "F5", True, Decimal("18000.00")),
            ("La Esquina", "F5", False, Decimal("15500.00")),
            ("Cancha Norte", "F7", False, Decimal("24000.00")),
            ("Los Álamos", "F8", False, Decimal("29000.00")),
            ("La Principal", "F11", False, Decimal("41000.00")),
        ]
        ahora = timezone.now()
        hoy = timezone.localdate()
        creados = 0
        for nombre, codigo, cubierta, precio in canchas:
            cancha, _ = Cancha.objects.get_or_create(
                nombre=nombre, defaults={"tipo": TipoCancha.objects.get(codigo=codigo), "cubierta": cubierta},
            )
            if not cancha.activa:
                continue
            for dias in (0, 1, 2):
                for hora in (17, 18, 19, 20, 21):
                    inicio = timezone.make_aware(datetime.combine(hoy + timedelta(days=dias), time(hora)))
                    if inicio <= ahora or Turno.objects.filter(
                        cancha=cancha, inicio__lt=inicio + timedelta(hours=1), fin__gt=inicio,
                    ).exists():
                        continue
                    publicar_turno(cancha.pk, inicio, precio)
                    creados += 1
        self.stdout.write(self.style.SUCCESS(f"{creados} turnos de demostración agregados."))
