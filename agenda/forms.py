from django import forms
from django.contrib.auth.forms import BaseUserCreationForm

from .models import Cancha, Reserva, TipoCancha, Turno, Usuario


class FechaInput(forms.DateInput):
    input_type = "date"


class RegistroForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ["nombre", "email", "telefono"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya hay una cuenta con ese correo.")
        return email


class DisponibilidadForm(forms.Form):
    modalidad = forms.ChoiceField(choices=TipoCancha.Codigo.choices)
    fecha = forms.DateField(widget=FechaInput(format="%Y-%m-%d"))


class FiltroAgendaForm(forms.Form):
    fecha = forms.DateField(required=False, widget=FechaInput(format="%Y-%m-%d"))
    cancha = forms.ModelChoiceField(queryset=Cancha.objects.all(), required=False)
    estado = forms.ChoiceField(choices=[("", "Todos")] + Reserva.Estado.choices, required=False)


class CanchaForm(forms.ModelForm):
    class Meta:
        model = Cancha
        fields = ["nombre", "tipo", "cubierta", "activa"]


class PrecioForm(forms.Form):
    precio = forms.DecimalField(label="Precio (ARS)", max_digits=10, decimal_places=2, min_value=0)


class PublicarForm(PrecioForm):
    cancha = forms.ModelChoiceField(queryset=Cancha.objects.filter(activa=True))
    inicio = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    field_order = ["cancha", "inicio", "precio"]


class MotivoForm(forms.Form):
    motivo = forms.CharField(max_length=200, widget=forms.Textarea(attrs={"rows": 3}))


class BloqueoForm(MotivoForm):
    cancelar_reserva = forms.BooleanField(
        required=False, label="Cancelar la reserva confirmada de este turno con el mismo motivo"
    )
