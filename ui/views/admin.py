from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "ui/dashboards/admin.html"
