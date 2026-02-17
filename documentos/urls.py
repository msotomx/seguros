from django.urls import path
from documentos.views import documento_download

app_name = "documentos"

urlpatterns = [
    path("<int:pk>/download/", documento_download, name="download"),
]
