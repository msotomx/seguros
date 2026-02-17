from django.views.generic import ListView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localdate

from ui.services.perms import can_see_comisiones
from finanzas.models import Comision


class ComisionListView(ListView):
    model = Comision
    template_name = "ui/finanzas/comision_list.html"
    context_object_name = "comisiones"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Comision.objects
            .select_related("poliza", "poliza__cliente", "poliza__aseguradora", "agente")
            .order_by("-created_at")
        )

        user = self.request.user
        if not can_see_comisiones(user):
            qs = qs.filter(agente=user)

        q = (self.request.GET.get("q") or "").strip()
        estatus = (self.request.GET.get("estatus") or "").strip()

        if q:
            qs = qs.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(poliza__cliente__nombre__icontains=q) |
                Q(agente__username__icontains=q)
            )

        if estatus:
            qs = qs.filter(estatus=estatus)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "estatus": self.request.GET.get("estatus", ""),
        }
        ctx["estatus_choices"] = Comision.Estatus.choices
        ctx["can_see_comisiones"] = can_see_comisiones(self.request.user)
        return ctx

@login_required
@require_POST
def comision_marcar_pagada(request, pk):
    comision = get_object_or_404(Comision, pk=pk)

    if not can_see_comisiones(request.user) and comision.agente_id != request.user.id:
        messages.error(request, "No tienes permisos para marcar esta comisión.")
        return redirect("ui:comision_list")

    if comision.estatus == Comision.Estatus.PAGADA:
        messages.info(request, "La comisión ya está pagada.")
        return redirect("ui:comision_list")

    comision.estatus = Comision.Estatus.PAGADA
    comision.fecha_pago = localdate()
    comision.save(update_fields=["estatus", "fecha_pago", "updated_at"])

    messages.success(request, "Comisión marcada como pagada.")
    return redirect("ui:comision_list")
