from __future__ import annotations

from django import forms
from crm.models import CodigoPostal


class CotizacionConductorForm(forms.Form):
    nombre = forms.CharField(
        required=True,
        max_length=120,
        label="Nombre(s)",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "given-name",
            }
        ),
    )

    apellido_paterno = forms.CharField(
        required=True,
        max_length=50,
        label="Apellido paterno",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "family-name",
            }
        ),
    )

    apellido_materno = forms.CharField(
        required=True,
        max_length=50,
        label="Apellido materno",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    rfc = forms.CharField(
        required=True,
        max_length=20,
        label="RFC",
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-uppercase",
                "autocomplete": "off",
            }
        ),
    )

    curp = forms.CharField(
        required=True,
        max_length=25,
        label="CURP",
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-uppercase",
                "autocomplete": "off",
            }
        ),
    )

    fecha_nacimiento = forms.DateField(
        required=True,
        label="Fecha de nacimiento",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    def clean_rfc(self):
        return (
            self.cleaned_data
            .get("rfc", "")
            .strip()
            .upper()
        )

    def clean_curp(self):
        return (
            self.cleaned_data
            .get("curp", "")
            .strip()
            .upper()
        )

class CotizacionDireccionForm(forms.Form):
    calle = forms.CharField(
        required=True,
        max_length=200,
        label="Calle",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "address-line1",
            }
        ),
    )

    num_ext = forms.CharField(
        required=True,
        max_length=20,
        label="Número",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    colonia = forms.ChoiceField(
        required=True,
        label="Colonia",
        choices=(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    def __init__(
        self,
        *args,
        codigo_postal: str,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        colonias = (
            CodigoPostal.objects
            .filter(
                codigo_postal=codigo_postal,
            )
            .exclude(
                colonia="",
            )
            .values_list(
                "colonia",
                flat=True,
            )
            .distinct()
            .order_by(
                "colonia",
            )
        )

        self.fields["colonia"].choices = [
            ("", "Selecciona colonia"),
            *[
                (colonia, colonia)
                for colonia in colonias
            ],
        ]

class CotizacionVehiculoForm(forms.Form):
    placas = forms.CharField(
        required=True,
        max_length=20,
        label="Número de placas",
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-uppercase",
                "autocomplete": "off",
            }
        ),
    )

    vin = forms.CharField(
        required=True,
        max_length=17,
        label="Número de serie / VIN",
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-uppercase",
                "autocomplete": "off",
            }
        ),
    )

    def clean_placas(self):
        return (
            self.cleaned_data
            .get("placas", "")
            .strip()
            .upper()
        )

    def clean_vin(self):
        return (
            self.cleaned_data
            .get("vin", "")
            .strip()
            .upper()
        )
