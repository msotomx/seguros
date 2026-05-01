from .dashboard import DashboardView, BasicDashboardView, AgenteDashboardView
from .dashboard import SupervisorDashboardView, AdminDashboardView

from .cotizaciones import (
    CotizacionListView,
    CotizacionDetailView,
    cotizacion_select_item,
    CotizacionWizardClienteSelectView,
    CotizacionWizardTipoView,
    CotizacionWizardVehiculoSelectView,
    cotizacion_calcular,
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
from ui.views.polizas import poliza_renovar, poliza_actualizar_vigencia, poliza_documento_subir
from ui.views.pagos import PagoListView, pago_marcar_pagado, pago_comprobante_subir
from finanzas.services.comisiones import marcar_comision_pagada
from ui.views.comisiones import ComisionListView, ComisionGenerarView, ComisionMarcarPagadaView
from ui.views.cobranza import CarteraVencidaListView, PagosPorVencerListView, pago_enviar_recordatorio
from ui.views.cobranza import pago_enviar_recordatorio_whatsapp, ReporteCobranzaAgenteView
from ui.views.cobranza import ReporteCobranzaAgenteDetalleView, ReporteCobranzaAgenteExcelView
from ui.views.cobranza import CobranzaMenuView, EstadoCuentaView
from ui.views.clientes import cliente_estado_cuenta_pdf
from ui.views.polizas import EndosoCreateView, EndosoUpdateView, EndosoDeleteView
from ui.views.reportes import ReporteMenuView, ReporteComisionesView, ReporteCarteraVencidaView
from ui.views.reportes import ReporteRenovacionesView, ReporteProduccionAgenteView, ReporteConversionAgenteView

__all__ = [
    "DashboardView",
    "BasicDashboardView",
    "AgenteDashboardView",
    "SupervisorDashboardView", 
    "AdminDashboardView",
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
    "poliza_documento_subir",
    "PagoListView",
    "pago_marcar_pagado",
    "pago_comprobante_subir",
    "ComisionListView",
    "marcar_comision_pagada",
    "CarteraVencidaListView",
    "PagosPorVencerListView",
    "pago_enviar_recordatorio",
    "pago_enviar_recordatorio_whatsapp",
    "CobranzaMenuView",
    "ReporteCobranzaAgenteView",
    "ReporteCobranzaAgenteDetalleView",
    "ReporteCobranzaAgenteExcelView",
    "cliente_estado_cuenta_pdf",
    "ComisionListView",
    "ComisionGenerarView",
    "ComisionMarcarPagadaView",
    "EndosoCreateView", "EndosoUpdateView", "EndosoDeleteView",
    "ReporteMenuView", "ReporteComisionesView", "ReporteCarteraVencidaView",
    "ReporteRenovacionesView", "ReporteProduccionAgenteView", "ReporteConversionAgenteView",
    "EstadoCuentaView",
]
