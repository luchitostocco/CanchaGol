from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import F, Q


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **datos):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        usuario = self.model(email=self.normalize_email(email).lower(), nombre=nombre, **datos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, nombre, password=None, **datos):
        datos["rol"] = Usuario.Rol.ADMIN
        return self.create_user(email, nombre, password, **datos)

    def get_by_natural_key(self, username):
        return self.get(email=username.strip().lower())


class Usuario(AbstractBaseUser):
    class Rol(models.TextChoices):
        CLIENTE = "CLIENTE", "Cliente"
        ADMIN = "ADMIN", "Administrador"

    id = models.AutoField(primary_key=True, db_column="id_usuario")
    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    password = models.CharField(max_length=255, db_column="clave_hash")
    rol = models.CharField(max_length=7, choices=Rol, default=Rol.CLIENTE)
    is_active = models.BooleanField(default=True, db_column="activo")

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        db_table = "usuario"
        constraints = [models.CheckConstraint(condition=Q(rol__in=["CLIENTE", "ADMIN"]), name="ck_usuario_rol")]

    @property
    def is_staff(self):
        return self.rol == self.Rol.ADMIN

    def __str__(self):
        return self.nombre


class TipoCancha(models.Model):
    class Codigo(models.TextChoices):
        F5 = "F5", "Fútbol 5"
        F7 = "F7", "Fútbol 7"
        F8 = "F8", "Fútbol 8"
        F11 = "F11", "Fútbol 11"

    id = models.AutoField(primary_key=True, db_column="id_tipo")
    codigo = models.CharField("modalidad", max_length=3, choices=Codigo, unique=True)

    class Meta:
        db_table = "tipo_cancha"
        constraints = [
            models.CheckConstraint(condition=Q(codigo__in=["F5", "F7", "F8", "F11"]), name="ck_tipo_codigo")
        ]

    def __str__(self):
        return self.get_codigo_display()


class Cancha(models.Model):
    id = models.AutoField(primary_key=True, db_column="id_cancha")
    tipo = models.ForeignKey(TipoCancha, on_delete=models.PROTECT, db_column="id_tipo", verbose_name="modalidad")
    nombre = models.CharField(max_length=60, unique=True)
    cubierta = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "cancha"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Turno(models.Model):
    id = models.AutoField(primary_key=True, db_column="id_turno")
    cancha = models.ForeignKey(Cancha, on_delete=models.PROTECT, db_column="id_cancha")
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    habilitado = models.BooleanField(default=True)
    motivo_bloqueo = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "turno"
        ordering = ["inicio", "cancha__nombre"]
        constraints = [
            models.UniqueConstraint(fields=["cancha", "inicio"], name="uq_cancha_inicio"),
            models.CheckConstraint(condition=Q(fin=F("inicio") + timedelta(hours=1)), name="ck_turno_duracion"),
            models.CheckConstraint(condition=Q(precio__gte=0), name="ck_turno_precio"),
        ]


class Reserva(models.Model):
    class Estado(models.TextChoices):
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"
        COMPLETADA = "COMPLETADA", "Completada"

    id = models.AutoField(primary_key=True, db_column="id_reserva")
    cliente = models.ForeignKey(Usuario, on_delete=models.PROTECT, db_column="id_cliente")
    turno = models.ForeignKey(Turno, on_delete=models.PROTECT, db_column="id_turno", related_name="reservas")
    creada_en = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=Estado, default=Estado.CONFIRMADA)
    importe_acordado = models.DecimalField(max_digits=10, decimal_places=2)
    cancelada_en = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.CharField(max_length=200, null=True, blank=True)
    turno_ocupado = models.GeneratedField(
        expression=models.Case(
            models.When(estado__in=["CONFIRMADA", "COMPLETADA"], then=F("turno_id")),
            default=models.Value(None),
        ),
        output_field=models.IntegerField(),
        db_persist=True,
        unique=True,
        null=True,
    )

    class Meta:
        db_table = "reserva"
        ordering = ["-turno__inicio", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(importe_acordado__gte=0), name="ck_reserva_importe"),
            models.CheckConstraint(
                condition=Q(estado__in=["CONFIRMADA", "CANCELADA", "COMPLETADA"]), name="ck_reserva_estado"
            ),
        ]

    def puede_cancelarse(self, ahora):
        return self.estado == self.Estado.CONFIRMADA and self.turno.inicio - ahora >= timedelta(hours=24)
