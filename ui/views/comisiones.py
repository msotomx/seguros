from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.db.models.functions import Coalesce
from django.db.models import Sum
from django.db.models import Q
from django.utils.dateparse import parse_date

from finanzas.models import Comision
from polizas.models import Poliza

from polizas.services import log_poliza_event
from ui.services.perms import can_see_comisiones
from finanzas.services.comisiones import generar_comision_poliza, marcar_comision_pagada


def resolver_agente_comision(poliza):
    return poliza.agente if getattr(poliza, "agente", None) else None

class ComisionGenerarView(View):
    def post(self, request, pk):
        poliza = get_object_or_404(Poliza, pk=pk)
        agente = poliza.agente

        if not agente:
            messages.error(request, "La póliza no tiene Agente Asignado.")
            return redirect("ui:poliza_detail", pk=poliza.pk)

        comision = generar_comision_poliza(
            poliza=poliza,
            agente=agente,
            usuario=request.user,
        )

        if comision:
            messages.success(request, "La comisión se generó correctamente.")
        else:
            messages.warning(request, "No fue posible generar la comisión.")

        return redirect("ui:poliza_detail", pk=poliza.pk)

class ComisionMarcarPagadaView(View):
    def post(self, request, pk):
        comision = get_object_or_404(
            Comision.objects.select_related("poliza"),
            pk=pk
        )

        notas = request.POST.get("notas", "").strip()
        fecha_pago_str = request.POST.get("fecha_pago", "").strip()
        fecha_pago = parse_date(fecha_pago_str) if fecha_pago_str else None

        marcar_comision_pagada(
            comision=comision,
            usuario=request.user,
            notas=notas,
        )

        messages.success(request, "La comisión se marcó como pagada.")

        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)

        return redirect("ui:comision_list")

class ComisionMarcarPagadaView2(View):
    def post(self, request, pk):
        comision = get_object_or_404(Comision.objects.select_related("poliza"), pk=pk)

        notas = request.POST.get("notas", "").strip()

        marcar_comision_pagada(
            comision=comision,
            usuario=request.user,
            notas=notas,
        )

        messages.success(request, "La comisión se marcó como pagada.")
        return redirect("ui:poliza_detail", pk=comision.poliza.pk)

User = get_user_model()


class ComisionListView(ListView):
    model = Comision
    template_name = "ui/finanzas/comision_list.html"
    context_object_name = "comisiones"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Comision.objects
            .select_related("poliza", "agente")
            .order_by("-fecha_generacion", "-id")
        )

        user = self.request.user

        if not user.has_perm("finanzas.manage_comisiones"):
            qs = qs.filter(agente=user)

        q = self.request.GET.get("q", "").strip()
        agente_id = self.request.GET.get("agente", "").strip()
        estatus = self.request.GET.get("estatus", "").strip()
        desde = self.request.GET.get("desde", "").strip()
        hasta = self.request.GET.get("hasta", "").strip()

        if q:
            qs = qs.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(agente__first_name__icontains=q) |
                Q(agente__last_name__icontains=q) |
                Q(agente__username__icontains=q)
            )

        if agente_id and user.has_perm("finanzas.manage_comisiones"):
            qs = qs.filter(agente_id=agente_id)

        if estatus:
            qs = qs.filter(estatus=estatus)

        if desde:
            qs = qs.filter(fecha_generacion__gte=desde)

        if hasta:
            qs = qs.filter(fecha_generacion__lte=hasta)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        qs_filtrado = self.get_queryset()

        context["agentes"] = User.objects.filter(
            comisiones__isnull=False
        ).distinct().order_by("first_name", "last_name", "username")

        context["q"] = self.request.GET.get("q", "").strip()
        context["agente_id"] = self.request.GET.get("agente", "").strip()
        context["estatus"] = self.request.GET.get("estatus", "").strip()
        context["desde"] = self.request.GET.get("desde", "").strip()
        context["hasta"] = self.request.GET.get("hasta", "").strip()

        context["total_comisiones"] = qs_filtrado.count()

        context["total_pendiente"] = qs_filtrado.filter(
            estatus=Comision.Estatus.PENDIENTE
        ).aggregate(
            total=Coalesce(Sum("monto_comision"), Decimal("0.00"))
        )["total"]

        context["total_pagado"] = qs_filtrado.filter(
            estatus=Comision.Estatus.PAGADA
        ).aggregate(
            total=Coalesce(Sum("monto_comision"), Decimal("0.00"))
        )["total"]

        return context
