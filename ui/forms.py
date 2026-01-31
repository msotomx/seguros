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


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo_cliente",
            "nombre_comercial",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "contacto_nombre",
            "contacto_email",
            "contacto_telefono",
            "rfc",
            "curp",
            "email_principal",
            "telefono_principal",
            "estatus",
            "origen",
            "portal_activo",
            "user_portal",
            "owner",
            "notas",
        ]
        widgets = {
            "tipo_cliente": forms.Select(attrs={"class": "form-select"}),
            "estatus": forms.Select(attrs={"class": "form-select"}),
            "portal_activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notas": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap para inputs estándar
        for name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ["CheckboxInput", "Select"]:
                field.widget.attrs.setdefault("class", "form-control")

        # Placeholders útiles (opcional)
        self.fields["nombre_comercial"].widget.attrs.setdefault("placeholder", "Ej. Ferretería López SA de CV")
        self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej. Juan")
        self.fields["apellido_paterno"].widget.attrs.setdefault("placeholder", "Ej. Pérez")
        self.fields["email_principal"].widget.attrs.setdefault("placeholder", "correo@dominio.com")
        self.fields["telefono_principal"].widget.attrs.setdefault("placeholder", "10 dígitos")

    def clean(self):
        cleaned = super().clean()

        tipo = (cleaned.get("tipo_cliente") or "").strip()

        # Normaliza strings (evita "   ")
        def norm(v):
            return (v or "").strip()

        nombre_comercial = norm(cleaned.get("nombre_comercial"))
        nombre = norm(cleaned.get("nombre"))
        ap_pat = norm(cleaned.get("apellido_paterno"))
        rfc = norm(cleaned.get("rfc"))
        curp = norm(cleaned.get("curp"))

        # Re-asigna normalizados
        cleaned["nombre_comercial"] = nombre_comercial
        cleaned["nombre"] = nombre
        cleaned["apellido_paterno"] = ap_pat
        cleaned["rfc"] = rfc
        cleaned["curp"] = curp

        # Validación por tipo
        if tipo == Cliente.TipoCliente.EMPRESA:
            if not nombre_comercial:
                self.add_error("nombre_comercial", "Para Empresa, el nombre comercial es obligatorio.")

            # Opcional: exigir RFC a empresas
            # (descomenta si lo quieres obligatorio)
            # if not rfc:
            #     self.add_error("rfc", "Para Empresa, el RFC es obligatorio.")

            # Recomendación: para empresa, nombre/apellidos pueden quedar vacíos.
            # No los forzamos.

        elif tipo == Cliente.TipoCliente.PERSONA:
            if not nombre:
                self.add_error("nombre", "Para Persona, el nombre es obligatorio.")
            if not ap_pat:
                self.add_error("apellido_paterno", "Para Persona, el apellido paterno es obligatorio.")

            # Opcional: exigir CURP a persona
            # (descomenta si lo quieres obligatorio)
            # if not curp:
            #     self.add_error("curp", "Para Persona, la CURP es obligatoria.")

            # Recomendación: nombre_comercial puede quedar vacío.

        else:
            # Si por alguna razón llega vacío/incorrecto
            self.add_error("tipo_cliente", "Selecciona el tipo de cliente.")

        return cleaned
