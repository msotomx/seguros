from django.utils import timezone
from django.views.generic import TemplateView

from portal.mixins import ClientePortalRequiredMixin
from cotizador.models import Cotizacion
from polizas.models import Poliza
from crm.models import Cliente
from finanzas.models import Pago

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class PortalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_cliente(self):
        try:
            c = Cliente.objects.get(user_portal=self.request.user)
        except Cliente.DoesNotExist:
            raise PermissionDenied("No tienes perfil de cliente portal.")
        if not c.portal_activo:
            raise PermissionDenied("Tu acceso al portal está desactivado.")
        return c

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self.get_cliente()
        today = timezone.localdate()

        # Cotizaciones activas (si aún las quieres mostrar)
        cotizaciones_activas = (
            Cotizacion.objects
            .filter(cliente=cliente)
            .exclude(estatus=Cotizacion.Estatus.RECHAZADA)
            .order_by("-created_at")[:10]
        )
        ctx["cotizaciones_activas"] = cotizaciones_activas
        ctx["cotizaciones_activas_count"] = cotizaciones_activas.count()

        # Pólizas vigentes (incluye documento)
        polizas_vigentes = (
            Poliza.objects
            .filter(cliente=cliente, estatus=Poliza.Estatus.VIGENTE,
                    vigencia_desde__lte=today, vigencia_hasta__gte=today)
            .select_related("aseguradora", "documento")
            .order_by("vigencia_hasta")[:10]
        )
        ctx["polizas_vigentes"] = polizas_vigentes
        ctx["polizas_vigentes_count"] = polizas_vigentes.count()

        # Pagos pendientes/vencidos (próximos 12)
        pagos_pendientes = (
            Pago.objects
            .filter(poliza__cliente=cliente, estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.VENCIDO])
            .select_related("poliza", "poliza__aseguradora", "comprobante")
            .order_by("fecha_programada")[:12]
        )
        ctx["pagos_pendientes"] = pagos_pendientes
        ctx["pagos_pendientes_count"] = pagos_pendientes.count()

        # Pagos pagados recientes
        pagos_pagados = (
            Pago.objects
            .filter(poliza__cliente=cliente, estatus=Pago.Estatus.PAGADO)
            .select_related("poliza", "poliza__aseguradora", "comprobante")
            .order_by("-fecha_pago", "-id")[:10]
        )
        ctx["pagos_pagados"] = pagos_pagados

        return ctx


class PortalDashboardView2(ClientePortalRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self.cliente
        ctx["cliente"] = cliente

        hoy = timezone.localdate()

        # ===== Cotizaciones activas (ENVIADA / ACEPTADA y vigencia vigente) =====
        cotizaciones_activas_qs = (
            Cotizacion.objects
            .filter(
                cliente=cliente,
                estatus__in=[Cotizacion.Estatus.ENVIADA, Cotizacion.Estatus.ACEPTADA],
                vigencia_hasta__gte=hoy,
            )
            .order_by("-created_at")
        )
        ctx["cotizaciones_activas_count"] = cotizaciones_activas_qs.count()
        ctx["cotizaciones_activas"] = cotizaciones_activas_qs[:5]

        # ===== Pólizas vigentes =====
        # Regla:
        # - por fechas 
        polizas_vigentes_qs = Poliza.objects.filter(
            cliente=cliente,
            vigencia_desde__lte=hoy,
            vigencia_hasta__gte=hoy,
        ).exclude(estatus=Poliza.Estatus.CANCELADA)

        ctx["polizas_vigentes_count"] = polizas_vigentes_qs.count()
        ctx["polizas_vigentes"] = polizas_vigentes_qs[:5]

        # ===== Recibos pendientes =====
        # Aún no existe modelo: lo dejamos como placeholder
        ctx["recibos_pendientes_count"] = None
        ctx["recibos_pendientes"] = []

        return ctx
