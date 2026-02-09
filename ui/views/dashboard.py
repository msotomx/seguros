from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.utils.timezone import localdate
from datetime import timedelta

from ui.services.dashboard import agente_kpis
from cotizador.models import Cotizacion
from polizas.models import Poliza

def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

def is_internal(user) -> bool:
    return (
        user.is_authenticated and (
            user.is_superuser
            or user_in_group(user, "Admin")
            or user_in_group(user, "Supervisor")
            or user_in_group(user, "Agente")
        )
    )

class DashboardView(LoginRequiredMixin, TemplateView):

    def dispatch(self, request, *args, **kwargs):
        if not is_internal(request.user):
            # si es un cliente autenticado (o usuario sin rol interno), mándalo al portal
            return redirect("portal:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        u = self.request.user
        if u.is_superuser or user_in_group(u, "Admin"):
            return ["ui/dashboard/admin.html"]
        if user_in_group(u, "Supervisor"):
            return ["ui/dashboard/supervisor.html"]
        if user_in_group(u, "Agente"):
            return ["ui/dashboard/agente.html"]
        return ["ui/dashboard/basic.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_superuser or user_in_group(user, "Admin"):
            ctx["role_label"] = "Admin"
        elif user_in_group(user, "Supervisor"):
            ctx["role_label"] = "Supervisor"
        elif user_in_group(user, "Agente"):
            ctx["role_label"] = "Agente"
        else:
            ctx["role_label"] = "Lectura"

        # KPIs Agente solo para agente
        ctx["kpi"] = agente_kpis(user)

        return ctx

