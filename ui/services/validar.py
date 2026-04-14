# Valida el documento a subir, para pagos, polizas
from django.core.exceptions import ValidationError

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def validar_archivo_comprobante(uploaded_file):
    if not uploaded_file:
        raise ValidationError("Selecciona un archivo para subir.")

    if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Solo se permiten archivos PDF, JPG o PNG.")

    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError("El archivo excede el tamaño máximo permitido de 5 MB.")
    
