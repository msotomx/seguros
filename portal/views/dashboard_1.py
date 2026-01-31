from django.utils import timezone
from django.views.generic import TemplateView

from cotizador.models import Cotizacion
from portal.mixins import ClientePortalRequiredMixin  # ajusta si tu mixin vive en otra ruta


class PortalDashboardView(ClientePortalRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self.cliente
        ctx["cliente"] = cliente

        hoy = timezone.localdate()

        # Cotizaciones activas (portal)
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

        return ctx
