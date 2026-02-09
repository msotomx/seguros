from django import forms
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils import timezone

from .forms_mixins import BootstrapFormMixin
from autos.models import Vehiculo, VehiculoCatalogo
from crm.models import Cliente
from cotizador.models import Cotizacion


class VehiculoFromCatalogoForm(forms.ModelForm):
    """
    Form mínimo para crear un Vehiculo a partir del catálogo
    durante el wizard de cotización.
    """

    # Campo auxiliar (no es FK directa en Vehiculo)
    catalogo_id = forms.ModelChoiceField(
        queryset=VehiculoCatalogo.objects.filter(is_active=True),
        label="Versión",
        required=True,
    )

    class Meta:
        model = Vehiculo   # 🔴 ESTA LÍNEA ES LA CLAVE
        fields = [
            "tipo_uso",
            "placas",
            "vin",
            "color",
            "valor_comercial",
        ]

class VehiculoFromCatalogoForm2(BootstrapFormMixin, forms.ModelForm):
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

from datetime import timedelta

class CotizacionDatosForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ["vigencia_desde", "vigencia_hasta", "forma_pago_preferida", "notas"]

        widgets = {
            "vigencia_desde": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "vigencia_hasta": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
#            "vigencia_desde": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
#            "vigencia_hasta": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "forma_pago_preferida": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Contado / Mensual"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vigencia_desde"].input_formats = ["%Y-%m-%d"]
        self.fields["vigencia_hasta"].input_formats = ["%Y-%m-%d"]
        # Solo en GET (no bound) y solo si vienen vacías en la instancia
        if not self.is_bound:
            today = timezone.localdate()

            if not self.instance.vigencia_desde:
                self.initial.setdefault("vigencia_desde", today)

            if not self.instance.vigencia_hasta:
                self.initial.setdefault("vigencia_hasta", today + timedelta(days=365))

            if not (self.instance.forma_pago_preferida or "").strip():
                self.initial.setdefault("forma_pago_preferida", "CONTADO")
    
    def clean(self):
        cleaned = super().clean()
        d = cleaned.get("vigencia_desde")
        h = cleaned.get("vigencia_hasta")
        if d and h and h <= d:
            self.add_error("vigencia_hasta", "La vigencia hasta debe ser mayor a la vigencia desde.")
        return cleaned

    @staticmethod
    def initial_defaults():
        today = timezone.localdate()
        return {
            "vigencia_desde": today,
            "vigencia_hasta": today + timedelta(days=365),
            "forma_pago_preferida": "CONTADO",
        }
