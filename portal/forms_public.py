from django import forms
from crm.models import Cliente
from cotizador.models import Cotizacion

from django import forms
from crm.models import Cliente
from autos.models import Marca, SubMarca, VehiculoCatalogo, Vehiculo
from datetime import date

def anios_choices(desde=2000, hasta=None):
    if hasta is None:
        hasta = date.today().year + 2
    return [(y, y) for y in range(hasta, desde - 1, -1)]

class CotizacionPublicaForm(forms.Form):
    # ===== Datos prospecto =====
    tipo_cliente = forms.ChoiceField(
        choices=Cliente.TipoCliente.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    nombre = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    apellido_paterno = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    apellido_materno = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    nombre_comercial = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    telefono = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))

    # ===== Vehículo (catálogo) =====
    tipo_uso = forms.ChoiceField(
        choices=Vehiculo.TipoUso.choices,
        initial=Vehiculo.TipoUso.PARTICULAR,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    marca = forms.ModelChoiceField(
        queryset=Marca.objects.filter(is_active=True).order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Selecciona marca",
    )

    submarca = forms.ModelChoiceField(
        queryset=SubMarca.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Selecciona submarca",
        required=True,
    )
    modelo_anio = forms.ChoiceField(
        choices=[("", "Selecciona año")] + anios_choices(2000),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Año"
    )

    catalogo = forms.ModelChoiceField(
        queryset=VehiculoCatalogo.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Selecciona versión",
        required=True,
    )

    placas = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    vin = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    notas = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))

    def clean(self):
        data = super().clean()

        if data.get("tipo_cliente") == Cliente.TipoCliente.PERSONA:
            if not data.get("nombre") or not data.get("apellido_paterno"):
                raise forms.ValidationError("Para persona, nombre y apellido paterno son requeridos.")

        if data.get("tipo_cliente") == Cliente.TipoCliente.EMPRESA:
            if not data.get("nombre_comercial"):
                raise forms.ValidationError("Para empresa, el nombre comercial es requerido.")

        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si viene POST (self.data) recargamos los querysets para que validen
        data = self.data or None

        # 1) Submarcas por marca
        marca_id = data.get("marca") if data else None
        if marca_id:
            self.fields["submarca"].queryset = SubMarca.objects.filter(
                marca_id=marca_id, is_active=True
            ).order_by("nombre")
        else:
            self.fields["submarca"].queryset = SubMarca.objects.none()

        # 2) VehiculoCatalogo por marca + submarca + anio
        submarca_id = data.get("submarca") if data else None
        anio = data.get("modelo_anio") if data else None

        if marca_id and submarca_id and anio:
            self.fields["catalogo"].queryset = VehiculoCatalogo.objects.filter(
                marca_id=marca_id,
                submarca_id=submarca_id,
                anio=anio,
                is_active=True,
            ).order_by("version")
        else:
            self.fields["catalogo"].queryset = VehiculoCatalogo.objects.none()
