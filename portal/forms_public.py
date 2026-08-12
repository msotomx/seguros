from datetime import date

from django import forms

from autos.models import (
    Marca,
    SubMarca,
    VehiculoCatalogo,
)
from cotizador.models import Cotizacion
from crm.models import CodigoPostal


def anios_choices(desde=2000, hasta=None):
    if hasta is None:
        hasta = date.today().year + 2

    return [
        (anio, anio)
        for anio in range(hasta, desde - 1, -1)
    ]


class CotizacionPublicaForm(forms.Form):
    """
    Formulario público con los datos mínimos necesarios
    para solicitar una cotización.

    Los datos completos para emisión se solicitarán
    posteriormente, después de seleccionar una opción.
    """

    # =====================================================
    # Datos del conductor / prospecto
    # =====================================================

    nombre = forms.CharField(
        required=True,
        max_length=120,
        label="Nombre",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nombre",
                "autocomplete": "given-name",
            }
        ),
    )

    genero = forms.ChoiceField(
        required=True,
        label="Género",
        choices=Cotizacion.GeneroConductor.choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com",
                "autocomplete": "email",
            }
        ),
    )

    telefono = forms.CharField(
        required=True,
        max_length=30,
        label="Teléfono",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Teléfono",
                "autocomplete": "tel",
                "inputmode": "tel",
            }
        ),
    )

    edad = forms.IntegerField(
        required=True,
        label="Edad",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
            }
        ),
    )

    codigo_postal = forms.CharField(
        required=True,
        min_length=5,
        max_length=5,
        label="Código Postal",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej. 32500",
                "maxlength": "5",
                "inputmode": "numeric",
                "autocomplete": "postal-code",
            }
        ),
    )

    # =====================================================
    # Vehículo
    # =====================================================

    marca = forms.ModelChoiceField(
        required=True,
        queryset=Marca.objects.filter(
            is_active=True
        ).order_by("nombre"),
        label="Marca",
        empty_label="Selecciona marca",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    submarca = forms.ModelChoiceField(
        required=True,
        queryset=SubMarca.objects.none(),
        label="SubMarca",
        empty_label="Selecciona submarca",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    modelo_anio = forms.ChoiceField(
        required=True,
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
        required=True,
        queryset=VehiculoCatalogo.objects.none(),
        label="Versión",
        empty_label="Selecciona versión",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # =====================================================
    # Inicialización dinámica de catálogos
    # =====================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data if self.is_bound else None

        marca_id = (
            data.get("marca")
            if data
            else None
        )

        submarca_id = (
            data.get("submarca")
            if data
            else None
        )

        modelo_anio = (
            data.get("modelo_anio")
            if data
            else None
        )

        # ---------------------------------------------
        # Submarcas correspondientes a la marca
        # ---------------------------------------------

        if marca_id:
            self.fields["submarca"].queryset = (
                SubMarca.objects.filter(
                    marca_id=marca_id,
                    is_active=True,
                )
                .order_by("nombre")
            )
        else:
            self.fields["submarca"].queryset = (
                SubMarca.objects.none()
            )

        # ---------------------------------------------
        # Versiones correspondientes a
        # marca + submarca + año
        # ---------------------------------------------

        if (
            marca_id
            and submarca_id
            and modelo_anio
        ):
            self.fields["catalogo"].queryset = (
                VehiculoCatalogo.objects.filter(
                    marca_id=marca_id,
                    submarca_id=submarca_id,
                    anio=modelo_anio,
                    is_active=True,
                )
                .order_by("version")
            )
        else:
            self.fields["catalogo"].queryset = (
                VehiculoCatalogo.objects.none()
            )

    # =====================================================
    # Validaciones
    # =====================================================

    def clean_codigo_postal(self):
        codigo_postal = (
            self.cleaned_data
            .get("codigo_postal", "")
            .strip()
        )

        if (
            len(codigo_postal) != 5
            or not codigo_postal.isdigit()
        ):
            raise forms.ValidationError(
                "El código postal debe contener "
                "exactamente 5 dígitos."
            )

        if not CodigoPostal.objects.filter(
            codigo_postal=codigo_postal
        ).exists():
            raise forms.ValidationError(
                "No encontramos el código postal indicado."
            )

        return codigo_postal

    def clean_nombre(self):
        nombre = (
            self.cleaned_data
            .get("nombre", "")
            .strip()
        )

        if not nombre:
            raise forms.ValidationError(
                "El nombre es obligatorio."
            )

        return nombre

    def clean_email(self):
        email = (
            self.cleaned_data
            .get("email", "")
            .strip()
            .lower()
        )

        return email

    def clean_telefono(self):
        telefono = (
            self.cleaned_data
            .get("telefono", "")
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
        modelo_anio = cleaned_data.get(
            "modelo_anio"
        )
        catalogo = cleaned_data.get("catalogo")

        if catalogo is None:
            return cleaned_data

        # La versión seleccionada es la autoridad.
        # Verificamos que corresponda a las selecciones
        # realizadas anteriormente.

        if (
            marca is not None
            and catalogo.marca_id != marca.id
        ):
            self.add_error(
                "catalogo",
                "La versión seleccionada no corresponde "
                "a la marca indicada.",
            )

        if (
            submarca is not None
            and catalogo.submarca_id != submarca.id
        ):
            self.add_error(
                "catalogo",
                "La versión seleccionada no corresponde "
                "a la submarca indicada.",
            )

        if (
            modelo_anio
            and str(catalogo.anio)
            != str(modelo_anio)
        ):
            self.add_error(
                "catalogo",
                "La versión seleccionada no corresponde "
                "al modelo-año indicado.",
            )

        return cleaned_data
