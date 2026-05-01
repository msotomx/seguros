from django import forms
from polizas.models import Endoso
from django.utils import timezone


class EndosoForm(forms.ModelForm):
    class Meta:
        model = Endoso
        fields = [
            "tipo_endoso",
            "fecha",
            "prima_ajuste",
            "descripcion",
        ]
        widgets = {
            "tipo_endoso": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"}
            ),
            "prima_ajuste": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

        labels = {
            "tipo_endoso": "Tipo de endoso",
            "fecha": "Fecha",
            "prima_ajuste": "Ajuste de prima",
            "descripcion": "Descripción",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]

        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.localdate()

    def clean_prima_ajuste(self):
        valor = self.cleaned_data.get("prima_ajuste")
        if valor is None:
            return 0
        return valor

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser futura.")
        return fecha