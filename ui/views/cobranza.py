from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils.timezone import localdate
from django.views.generic import ListView
from datetime import timedelta

from finanzas.models import Pago
from ui.services.perms import can_see_pagos


class CarteraVencidaListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/cobranza/cartera_vencida.html"
    context_object_name = "pagos"
    paginate_by = 30

    def get_queryset(self):
        qs = (
            Pago.objects
            .select_related(
                "poliza",
                "poliza__cliente",
                "poliza__agente",
                "poliza__aseguradora",
            )
            .filter(estatus=Pago.Estatus.VENCIDO)
            .order_by("fecha_vencimiento", "id")
        )

        user = self.request.user

        if not can_see_pagos(user):
            qs = qs.filter(poliza__agente=user)

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(poliza__cliente__nombre__icontains=q) |
                Q(poliza__cliente__apellido_paterno__icontains=q) |
                Q(poliza__cliente__apellido_materno__icontains=q) |
                Q(poliza__cliente__nombre_comercial__icontains=q) |
                Q(poliza__aseguradora__nombre__icontains=q) |
                Q(referencia__icontains=q)
            )

        agente_id = (self.request.GET.get("agente") or "").strip()
        if agente_id and can_see_pagos(user):
            qs = qs.filter(poliza__agente_id=agente_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = localdate()

        for p in context["object_list"]:
            p.dias_atraso = (hoy - p.fecha_vencimiento).days if p.fecha_vencimiento else 0

        base_qs = self.get_queryset()
        resumen = base_qs.aggregate(
            total_vencido=Coalesce(
                Sum("monto"),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
        )

        context["total_vencido"] = resumen["total_vencido"]
        context["cantidad_vencidos"] = base_qs.count()
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["hoy"] = hoy
        return context



class PagosPorVencerListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/cobranza/pagos_por_vencer.html"
    context_object_name = "pagos"
    paginate_by = 30

    def get_queryset(self):
        hoy = localdate()
        dias = self._get_dias()
        limite = hoy + timedelta(days=dias)

        qs = (
            Pago.objects
            .select_related(
                "poliza",
                "poliza__cliente",
                "poliza__agente",
                "poliza__aseguradora",
            )
            .filter(
                estatus__in=[
                    Pago.Estatus.PENDIENTE,
                    Pago.Estatus.PARCIAL,
                ],
                fecha_vencimiento__isnull=False,
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=limite,
            )
            .exclude(poliza__estatus="CANCELADA")
            .order_by("fecha_vencimiento", "id")
        )

        user = self.request.user

        if not can_see_pagos(user):
            qs = qs.filter(poliza__agente=user)

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(poliza__cliente__nombre__icontains=q) |
                Q(poliza__cliente__apellido_paterno__icontains=q) |
                Q(poliza__cliente__apellido_materno__icontains=q) |
                Q(poliza__cliente__nombre_comercial__icontains=q) |
                Q(poliza__aseguradora__nombre__icontains=q) |
                Q(referencia__icontains=q)
            )

        agente_id = (self.request.GET.get("agente") or "").strip()
        if agente_id and can_see_pagos(user):
            qs = qs.filter(poliza__agente_id=agente_id)

        return qs

    def _get_dias(self):
        try:
            dias = int(self.request.GET.get("dias", 7))
        except (TypeError, ValueError):
            dias = 7
        return max(dias, 1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = localdate()
        dias = self._get_dias()
        limite = hoy + timedelta(days=dias)

        for p in context["object_list"]:
            if p.fecha_vencimiento:
                p.dias_restantes = (p.fecha_vencimiento - hoy).days
            else:
                p.dias_restantes = None

        base_qs = self.get_queryset()
        resumen = base_qs.aggregate(
            total_por_vencer=Coalesce(
                Sum("monto"),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
        )

        context["total_por_vencer"] = resumen["total_por_vencer"]
        context["cantidad_por_vencer"] = base_qs.count()
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["dias"] = dias
        context["hoy"] = hoy
        context["limite"] = limite
        return context
