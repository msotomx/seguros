from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView, LogoutView

from portal.views.home import PortalHomeView
from portal.views.dashboard import PortalDashboardView
from portal.views.perfil import PortalPerfilView
from portal.views.cotizar import PortalCotizarCreateView
from portal.views.api import SubmarcasPorMarcaView, CatalogoPorFiltroView
from portal.views.cotizar_resumen import PortalCotizarResumenView
from portal.views.home import AccesoSuspendidoView
from portal.views.polizas import PortalPolizaListView

app_name = "portal"

urlpatterns = [
    path("", PortalHomeView.as_view(), name="home"),
    path("dashboard/", PortalDashboardView.as_view(), name="dashboard"),
    path("perfil/", PortalPerfilView.as_view(), name="perfil"),
    path("cotizar/", PortalCotizarCreateView.as_view(), name="cotizar"),
    path("api/submarcas/", SubmarcasPorMarcaView.as_view(), name="api_submarcas"),
    path("api/catalogo/", CatalogoPorFiltroView.as_view(), name="api_catalogo"),
    path("cotizar/resumen/", PortalCotizarResumenView.as_view(), name="cotizar_resumen"),

    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="accounts:login"), name="logout"),
    # si cliente no tiene portal_activo
    path("acceso-suspendido/", AccesoSuspendidoView.as_view(), name="acceso_suspendido"),
    path("polizas/", PortalPolizaListView.as_view(), name="poliza_list"),
]
