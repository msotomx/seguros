from django import forms
from documentos.models import Documento

class DocumentoUploadForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["tipo", "file", "nombre_archivo"]

    def clean(self):
        cleaned = super().clean()
        f = cleaned.get("file")
        if f and not cleaned.get("nombre_archivo"):
            cleaned["nombre_archivo"] = f.name
        return cleaned
