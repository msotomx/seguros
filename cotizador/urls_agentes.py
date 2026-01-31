from django.urls import path
from cotizador.views.agentes import AgenteCotizacionListView, AgenteCotizacionDetailView
from cotizador.views.agentes import AgenteConvertirClientePortalView

app_name = "cotizador_agentes"

urlpatterns = [
    path("cotizaciones/", AgenteCotizacionListView.as_view(), name="cotizacion_list"),
    path("cotizaciones/<str:folio>/", AgenteCotizacionDetailView.as_view(), name="cotizacion_detail"),
    path("cotizaciones/<str:folio>/convertir-portal/", AgenteConvertirClientePortalView.as_view(), name="cotizacion_convertir_portal"),
]
