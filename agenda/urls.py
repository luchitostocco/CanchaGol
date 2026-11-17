from django.contrib.auth import views as auth
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("ingresar/", auth.LoginView.as_view(template_name="agenda/ingresar.html"), name="ingresar"),
    path("salir/", auth.LogoutView.as_view(), name="salir"),
    path("turnos/<int:turno_id>/reservar/", views.reservar, name="reservar"),
    path("mis-reservas/", views.mis_reservas, name="mis_reservas"),
    path("mis-reservas/<int:reserva_id>/cancelar/", views.cancelar, name="cancelar"),
    path("gestion/", views.gestion, name="gestion"),
    path("gestion/canchas/nueva/", views.editar_cancha, name="nueva_cancha"),
    path("gestion/canchas/<int:cancha_id>/", views.editar_cancha, name="editar_cancha"),
    path("gestion/turnos/nuevo/", views.nuevo_turno, name="nuevo_turno"),
    path("gestion/turnos/<int:turno_id>/precio/", views.precio, name="precio"),
    path("gestion/turnos/<int:turno_id>/bloquear/", views.bloquear, name="bloquear"),
    path("gestion/turnos/<int:turno_id>/habilitar/", views.habilitar, name="habilitar"),
    path("gestion/reservas/<int:reserva_id>/cancelar/", views.cancelar_admin, name="cancelar_admin"),
    path("gestion/reservas/<int:reserva_id>/completar/", views.completar, name="completar"),
]
