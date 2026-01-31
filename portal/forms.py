from django import forms
from crm.models import Cliente
from .forms_mixins import BootstrapFormMixin


class PortalClientePerfilForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "telefono_principal",
            "direccion_contacto",
            "notas",
            "contacto_nombre",
            "contacto_email",
            "contacto_telefono",
        ]
        widgets = {
            "telefono_principal": forms.TextInput(attrs={"class": "form-control"}),
            "direccion_contacto": forms.Select(attrs={"class": "form-select"}),
            "contacto_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "contacto_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contacto_telefono": forms.TextInput(attrs={"class": "form-control"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "telefono_principal": "Teléfono",
            "direccion_contacto": "Dirección de contacto",
            "notas": "Notas",
            "contacto_nombre": "Nombre de contacto",
            "contacto_email": "Email de contacto",
            "contacto_telefono": "Teléfono de contacto",
        }
