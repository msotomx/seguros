from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AgenteDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "ui/dashboards/agente.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # KPIs del agente (mis cotizaciones, mis pólizas, renovaciones, etc.)
        return ctx
