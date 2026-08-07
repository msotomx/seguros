from datetime import date

from django import forms

from autos.models import Marca, SubMarca, VehiculoCatalogo
from cotizador.models import Cotizacion


def anios_choices(desde=2000, hasta=None):
    if hasta is None:
        hasta = date.today().year + 2

    return [
        (anio, anio)
        for anio in range(hasta, desde - 1, -1)
    ]


class CotizacionPublicaForm(forms.Form):
    # =====================================================
    # Datos del prospecto/conductor
    # =====================================================

    nombre = forms.CharField(
        required=True,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nombre",
            }
        ),
    )

    genero = forms.ChoiceField(
        required=True,
        choices=Cotizacion.GeneroConductor.choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    edad = forms.IntegerField(
        required=True,
        min_value=18,
        max_value=99,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "18",
                "max": "99",
                "inputmode": "numeric",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com",
            }
        ),
    )

    telefono = forms.CharField(
        required=True,
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Teléfono",
                "inputmode": "tel",
            }
        ),
    )

    codigo_postal = forms.CharField(
        required=True,
        min_length=5,
        max_length=5,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej. 32500",
                "maxlength": "5",
                "inputmode": "numeric",
            }
        ),
    )

    # =====================================================
    # Vehículo
    # =====================================================

    marca = forms.ModelChoiceField(
        queryset=Marca.objects.filter(
            is_active=True
        ).order_by("nombre"),
        empty_label="Selecciona marca",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    submarca = forms.ModelChoiceField(
        queryset=SubMarca.objects.none(),
        empty_label="Selecciona submarca",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    modelo_anio = forms.ChoiceField(
        choices=[
            ("", "Selecciona año"),
            *anios_choices(2000),
        ],
        label="Modelo-Año",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    catalogo = forms.ModelChoiceField(
        queryset=VehiculoCatalogo.objects.none(),
        empty_label="Selecciona versión",
        label="Versión",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        marca_id = self.data.get("marca") if self.is_bound else None
        submarca_id = (
            self.data.get("submarca")
            if self.is_bound
            else None
        )
        anio = (
            self.data.get("modelo_anio")
            if self.is_bound
            else None
        )

        if marca_id:
            self.fields["submarca"].queryset = (
                SubMarca.objects.filter(
                    marca_id=marca_id,
                    is_active=True,
                ).order_by("nombre")
            )

        if marca_id and submarca_id and anio:
            self.fields["catalogo"].queryset = (
                VehiculoCatalogo.objects.filter(
                    marca_id=marca_id,
                    submarca_id=submarca_id,
                    anio=anio,
                    is_active=True,
                ).order_by("version")
            )

    def clean_codigo_postal(self):
        codigo_postal = (
            self.cleaned_data["codigo_postal"]
            .strip()
        )

        if not codigo_postal.isdigit():
            raise forms.ValidationError(
                "El código postal debe contener cinco dígitos."
            )

        return codigo_postal

    def clean_telefono(self):
        telefono = (
            self.cleaned_data["telefono"]
            .strip()
        )

        if not telefono:
            raise forms.ValidationError(
                "El teléfono es obligatorio."
            )

        return telefono

    def clean(self):
        cleaned_data = super().clean()

        marca = cleaned_data.get("marca")
        submarca = cleaned_data.get("submarca")
        catalogo = cleaned_data.get("catalogo")
        modelo_anio = cleaned_data.get("modelo_anio")

        if not catalogo:
            return cleaned_data

        if marca and catalogo.marca_id != marca.id:
            self.add_error(
                "catalogo",
                "La versión no corresponde a la marca seleccionada.",
            )

        if (
            submarca
            and catalogo.submarca_id != submarca.id
        ):
            self.add_error(
                "catalogo",
                "La versión no corresponde a la submarca seleccionada.",
            )

        if (
            modelo_anio
            and str(catalogo.anio) != str(modelo_anio)
        ):
            self.add_error(
                "catalogo",
                "La versión no corresponde al año seleccionado.",
            )

        return cleaned_data
