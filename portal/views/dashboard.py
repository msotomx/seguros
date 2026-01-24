from django.views.generic import TemplateView
from portal.mixins import ClientePortalRequiredMixin


class PortalDashboardView(ClientePortalRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cliente"] = self.cliente
        return ctx
