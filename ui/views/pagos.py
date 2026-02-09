from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView
from django.utils.timezone import localdate
from datetime import timedelta

from finanzas.models import Pago
from ui.services.perms import can_manage_pagos

class PagoListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/finanzas/pago_list.html"
    context_object_name = "pagos"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Pago.objects
            .select_related("poliza", "poliza__cliente", "poliza__aseguradora")
            .order_by("-fecha_programada", "-created_at")
        )

        user = self.request.user
        # Alcance: agente ve sus pólizas; supervisor/admin ve todo
        if not can_manage_pagos(user):
            qs = qs.filter(poliza__agente=user)

        # Filtros
        q = (self.request.GET.get("q") or "").strip()
        estatus = (self.request.GET.get("estatus") or "").strip()
        desde = (self.request.GET.get("desde") or "").strip()
        hasta = (self.request.GET.get("hasta") or "").strip()

        if q:
            qs = qs.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(poliza__cliente__nombre__icontains=q) |
                Q(referencia__icontains=q)
            )

        if estatus:
            qs = qs.filter(estatus=estatus)

        if desde:
            qs = qs.filter(fecha_programada__gte=desde)

        if hasta:
            qs = qs.filter(fecha_programada__lte=hasta)

        # Auto “Vencido” (opcional visual, sin guardar): solo filtra si lo pides
        # Nota: lo correcto es tener un job que marque vencidos.
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "estatus": self.request.GET.get("estatus", ""),
            "desde": self.request.GET.get("desde", ""),
            "hasta": self.request.GET.get("hasta", ""),
        }
        ctx["estatus_choices"] = Pago.Estatus.choices
        return ctx
