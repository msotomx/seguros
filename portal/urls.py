from django.urls import path
from .views.dashboard import PortalDashboardView
from .views.perfil import PortalPerfilView

app_name = "portal"

urlpatterns = [
    path("", PortalDashboardView.as_view(), name="dashboard"),
    path("perfil/", PortalPerfilView.as_view(), name="perfil"),
]
