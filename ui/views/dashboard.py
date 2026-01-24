from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView
from ui.services.dashboard import agente_kpis
from crm.models import Cliente
from cotizador.models import Cotizacion
from polizas.models import Poliza, Incidente, Siniestro
from finanzas.models import Pago


def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

class DashboardView(LoginRequiredMixin, TemplateView):
    # template dinámico

    def get_template_names(self):
        u = self.request.user
        if u.is_superuser or user_in_group(u, "Admin"):
            return ["ui/dashboard/admin.html"]   # luego lo creamos
        if user_in_group(u, "Supervisor"):
            return ["ui/dashboard/supervisor.html"]  # luego lo creamos
        if user_in_group(u, "Agente"):
            return ["ui/dashboard/agente.html"]
        return ["ui/dashboard/basic.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # etiqueta rol (para navbar)
        if user.is_superuser or user_in_group(user, "Admin"):
            ctx["role_label"] = "Admin"
        elif user_in_group(user, "Supervisor"):
            ctx["role_label"] = "Supervisor"
        elif user_in_group(user, "Agente"):
            ctx["role_label"] = "Agente"
        else:
            ctx["role_label"] = "Lectura"

        # KPIs Agente
        if user_in_group(user, "Agente") or (not user_in_group(user, "Supervisor") and not user_in_group(user, "Admin") and not user.is_superuser):
            ctx["kpi"] = agente_kpis(user)

        return ctx
