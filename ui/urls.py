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
    cotizacion_calcular,
    cotizacion_emitir_poliza,
    PolizaListView,
    PolizaDetailView,
    CotizacionWizardDatosView,
    CotizacionItemDetailView,
    poliza_marcar_vigente,
    poliza_actualizar_numero,
    poliza_cancelar,
    poliza_renovar,
    poliza_actualizar_vigencia,
    PagoListView, 
    pago_marcar_pagado,
    ComisionListView,
    comision_marcar_pagada,
    poliza_documento_subir,
    pago_comprobante_subir,
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
    # Crear Cotizacion en ui, no desde portal
    path("cotizaciones/nueva/datos/", CotizacionWizardDatosView.as_view(), name="cotizacion_new_datos"),
    path("cotizaciones/item/<int:pk>/", CotizacionItemDetailView.as_view(), name="cotizacion_item_detail"),
    # Calcular cotizaciones
    path("cotizaciones/<int:pk>/calcular/", cotizacion_calcular, name="cotizacion_calcular"),
    path("cotizaciones/<int:pk>/emitir/", cotizacion_emitir_poliza, name="cotizacion_emitir_poliza"),
    # cambia el portal_activo del cliente
    path("clientes/<int:pk>/portal-toggle/", cliente_portal_toggle, name="cliente_portal_toggle"),
    # Clientes
    path("clientes/", ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", ClienteCreateView.as_view(), name="cliente_create"),
    path("clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="cliente_update"),
    path("clientes/<int:pk>/", ClienteDetailView.as_view(), name="cliente_detail"),
    # Polizas
    path("polizas/", PolizaListView.as_view(), name="poliza_list"),
    path("polizas/<int:pk>/", PolizaDetailView.as_view(), name="poliza_detail"),
    path("polizas/<int:pk>/marcar-vigente/", poliza_marcar_vigente, name="poliza_marcar_vigente"),
    path("polizas/<int:pk>/actualizar-numero/", poliza_actualizar_numero, name="poliza_actualizar_numero"),
    path("polizas/<int:pk>/cancelar/", poliza_cancelar, name="poliza_cancelar"),
    path("polizas/<int:pk>/renovar/", poliza_renovar, name="poliza_renovar"),
    path("polizas/<int:pk>/actualizar-vigencia/", poliza_actualizar_vigencia, name="poliza_actualizar_vigencia"),
    # Pagos
    path("pagos/", PagoListView.as_view(), name="pago_list"),
    path("pagos/<int:pk>/marcar-pagado/", pago_marcar_pagado, name="pago_marcar_pagado"),
    # Comisiones
    path("comisiones/", ComisionListView.as_view(), name="comision_list"),
    path("comisiones/<int:pk>/marcar-pagada/", comision_marcar_pagada, name="comision_marcar_pagada"),
    # Documentos
    path("polizas/<int:pk>/documento/subir/", poliza_documento_subir, name="poliza_documento_subir"),
    path("pagos/<int:pk>/comprobante/subir/", pago_comprobante_subir, name="pago_comprobante_subir"),


]
