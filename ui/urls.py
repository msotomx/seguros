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
    cliente_portal_toggle,
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDetailView,
)

app_name = "ui"

urlpatterns = [
    # ✅ Dashboard principal
    path("", DashboardView.as_view(), name="dashboard"),
    # Dashboard por rol
    path("dashboard/agente/", AgenteDashboardView.as_view(), name="dashboard_agente"),
    path("dashboard/supervisor/", SupervisorDashboardView.as_view(), name="dashboard_supervisor"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard_admin"),

    # Cotizaciones
    path("cotizaciones/", CotizacionListView.as_view(), name="cotizacion_list"),
    path("cotizaciones/<int:pk>/", CotizacionDetailView.as_view(), name="cotizacion_detail"),
    path("cotizaciones/<int:pk>/select/<int:item_id>/", cotizacion_select_item, name="cotizacion_select_item"),

    # Wizard: nueva cotización
    path("cotizaciones/nueva/cliente/", CotizacionWizardClienteSelectView.as_view(), name="cotizacion_new_cliente"),
    path("cotizaciones/nueva/cliente/crear/", ClienteQuickCreateView.as_view(), name="cliente_quick_create"),
    path("cotizaciones/nueva/tipo/", CotizacionWizardTipoView.as_view(), name="cotizacion_new_tipo"),
    path("cotizaciones/nueva/vehiculo/", CotizacionWizardVehiculoSelectView.as_view(), name="cotizacion_new_vehiculo"),
    # cambia el portal_activo del cliente
    path("clientes/<int:pk>/portal-toggle/", cliente_portal_toggle, name="cliente_portal_toggle"),
    #Clientes
    path("clientes/", ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", ClienteCreateView.as_view(), name="cliente_create"),
    path("clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="cliente_update"),
    path("clientes/<int:pk>/", ClienteDetailView.as_view(), name="cliente_detail"),
]
