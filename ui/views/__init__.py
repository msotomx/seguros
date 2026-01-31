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
)
from .clientes import (
    ClienteQuickCreateView, 
    cliente_portal_toggle, 
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDetailView,
)

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
]
