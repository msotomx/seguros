from .dashboard import DashboardView

from .agente import AgenteDashboardView
from .supervisor import SupervisorDashboardView
from .admin import AdminDashboardView

from .cotizaciones import (
    CotizacionListView,
    CotizacionDetailView,
    cotizacion_select_item,
    CotizacionWizardClienteSelectView,
    CotizacionWizardTipoView,
    CotizacionWizardVehiculoSelectView,
    cotizacion_calcular,
    cotizacion_emitir,
    cotizacion_emitir_poliza,
    CotizacionWizardDatosView,
    CotizacionItemDetailView,
)
from .clientes import (
    ClienteQuickCreateView, 
    cliente_portal_toggle, 
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDetailView,
)

from ui.views.polizas import PolizaListView, PolizaDetailView
from ui.views.polizas import poliza_marcar_vigente, poliza_actualizar_numero, poliza_cancelar
from ui.views.polizas import poliza_renovar, poliza_actualizar_vigencia
from ui.views.pagos import PagoListView

__all__ = [
    "DashboardView",
    "CotizacionListView",
    "CotizacionDetailView",
    "cotizacion_select_item",
    "CotizacionWizardClienteSelectView",
    "CotizacionWizardTipoView",
    "CotizacionWizardVehiculoSelectView",
    "ClienteQuickCreateView",
    "cliente_portal_toggle",
    "ClienteListView,"
    "ClienteCreateView",
    "ClienteUpdateView",
    "ClienteDetailView",
    "cotizacion_calcular",
    "cotizacion_emitir",
    "cotizacion_emitir_poliza",
    "PolizaListView",
    "PolizaDetailView",
    "CotizacionWizardDatosView",
    "CotizacionItemDetailView",
    "poliza_marcar_vigente",
    "poliza_actualizar_numero",
    "poliza_cancelar",
    "poliza_renovar",
    "poliza_actualizar_vigencia",
    "PagoListView",
]
