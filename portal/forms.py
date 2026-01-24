from django import forms
from crm.models import Cliente
from .forms_mixins import BootstrapFormMixin


class PortalClientePerfilForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo_cliente",
            "nombre_comercial",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "rfc",
            "telefono_principal",
            "email_principal",
            "origen",
            "notas",
        ]
