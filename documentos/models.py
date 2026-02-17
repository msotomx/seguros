from django.conf import settings
from django.db import models
from core.models import TimeStampedModel
from django.urls import reverse

# ---------------------------------------------------------------------
# Documentos / Archivos (adjuntos)
# ---------------------------------------------------------------------

class Documento(TimeStampedModel):
    class Tipo(models.TextChoices):
        PDF = "PDF", "PDF"
        IMG = "IMG", "Imagen"
        XML = "XML", "XML"
        DOC = "DOC", "Documento"
        OTRO = "OTRO", "Otro"

    nombre_archivo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.OTRO, db_index=True)
    file = models.FileField(upload_to="docs/%Y/%m/")
    tamano = models.PositiveIntegerField(default=0)
    hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos_subidos"
    )

    def get_absolute_url(self):
        return reverse("documentos:documento_download", args=[self.pk])

    class Meta:
        permissions = [
            ("download_documento", "Puede descargar documentos"),
        ]

