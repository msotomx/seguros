from django.urls import path
from documentos.views import documento_download, subir_endoso_pdf, ver_documento

app_name = "documentos"

urlpatterns = [
    path("<int:pk>/download/", documento_download, name="download"),
    path("endosos/<int:endoso_id>/subir-pdf/", subir_endoso_pdf, name="subir_endoso_pdf"),
    path("ver/<int:documento_id>/", ver_documento, name="ver_documento"),
]
