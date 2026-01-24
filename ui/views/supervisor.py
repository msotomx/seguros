from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class SupervisorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "ui/dashboards/supervisor.html"
