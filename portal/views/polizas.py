from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView

from crm.models import Cliente
from polizas.models import Poliza


class PortalPolizaListView(LoginRequiredMixin, ListView):
    template_name = "portal/poliza_list.html"
    context_object_name = "polizas"
    paginate_by = 20

    def _cliente_portal(self):
        try:
            c = Cliente.objects.get(user_portal=self.request.user)
        except Cliente.DoesNotExist:
            raise PermissionDenied("No tienes un perfil de cliente para el portal.")
        if not getattr(c, "portal_activo", False):
            raise PermissionDenied("Tu acceso al portal está desactivado.")
        return c

    def get_queryset(self):
        cliente = self._cliente_portal()
        return (
            Poliza.objects
            .filter(cliente=cliente)
            .select_related("aseguradora", "producto", "documento")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cliente"] = self._cliente_portal()
        return ctx
