from django import forms
from django.db.models import Q
from django.views.generic import TemplateView

from autos.models import Vehiculo, VehiculoCatalogo
from crm.models import Cliente
from .forms_mixins import BootstrapFormMixin


class VehiculoFromCatalogoForm(BootstrapFormMixin, forms.ModelForm):
    catalogo_id = forms.IntegerField()
    tipo_uso = forms.ChoiceField(choices=Vehiculo.TipoUso.choices)
    placas = forms.CharField(required=False, max_length=20)
    vin = forms.CharField(required=False, max_length=40)
    color = forms.CharField(required=False, max_length=40)
    valor_comercial = forms.DecimalField(required=False, max_digits=14, decimal_places=2)


class ClienteQuickCreateForm(BootstrapFormMixin, forms.ModelForm):
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
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


#class ClienteQuickCreateForm(forms.ModelForm):
#    class Meta:
#        model = Cliente
#        fields = [
#            "tipo_cliente",
#            "nombre_comercial",
#            "nombre",
#            "apellido_paterno",
#            "apellido_materno",
#            "rfc",
#            "email_principal",
#            "telefono_principal",
#            "origen",
#            "notas",
#        ]
#        widgets = {
#            "notas": forms.Textarea(attrs={"rows": 3}),
#        }
#
#    def clean(self):
#        cleaned = super().clean()
#        tipo = cleaned.get("tipo_cliente")
#        if tipo == Cliente.TipoCliente.EMPRESA:
#            if not (cleaned.get("nombre_comercial") or "").strip():
#                self.add_error("nombre_comercial", "Requerido para empresas.")
#        elif tipo == Cliente.TipoCliente.PERSONA:
#            if not (cleaned.get("nombre") or "").strip():
#                self.add_error("nombre", "Requerido para persona.")
#        return cleaned
