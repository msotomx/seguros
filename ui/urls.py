from django.urls import path

from .views import (
    DashboardView,
    AgenteDashboardView,
    SupervisorDashboardView,
    AdminDashboardView,
    CotizacionListView,
    CotizacionDetailView,
    cotizacion_select_item,
    CotizacionWizardClienteSelectView,
    ClienteQuickCreateView,
    CotizacionWizardTipoView,
    CotizacionWizardVehiculoSelectView,
)

app_name = "ui"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("cotizaciones/", CotizacionListView.as_view(), name="cotizacion_list"),
    path("cotizaciones/<int:pk>/", CotizacionDetailView.as_view(), name="cotizacion_detail"),
    path("cotizaciones/<int:pk>/select/<int:item_id>/", cotizacion_select_item, name="cotizacion_select_item"),

    # Wizard: nueva cotización
    path("cotizaciones/nueva/cliente/", CotizacionWizardClienteSelectView.as_view(), name="cotizacion_new_cliente"),
    path("cotizaciones/nueva/cliente/crear/", ClienteQuickCreateView.as_view(), name="cliente_quick_create"),
    path("cotizaciones/nueva/vehiculo/", DashboardView.as_view(), name="cotizacion_new_vehiculo"),  # placeholder
    path("cotizaciones/nueva/tipo/", CotizacionWizardTipoView.as_view(), name="cotizacion_new_tipo"),
    path("cotizaciones/nueva/vehiculo/", CotizacionWizardVehiculoSelectView.as_view(), name="cotizacion_new_vehiculo"),
    #path("cotizaciones/nueva/datos/", DashboardView.as_view(), name="cotizacion_new_datos"),  # placeholder paso 4

    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/agente/", AgenteDashboardView.as_view(), name="dashboard_agente"),
    path("dashboard/supervisor/", SupervisorDashboardView.as_view(), name="dashboard_supervisor"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard_admin"),
]
