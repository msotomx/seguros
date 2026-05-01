from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils.timezone import localdate
from django.views.generic import ListView
from django.views.generic import TemplateView
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST


from finanzas.models import Pago
from crm.models import Cliente
from polizas.models import Poliza

from ui.services.perms import can_see_pagos, can_manage_pago
from finanzas.services.recordatorios import registrar_recordatorio_pago
from finanzas.services.recordatorios_whatsapp import enviar_recordatorio_whatsapp
from ui.services.pdf import render_to_pdf


class CobranzaMenuView(TemplateView):
    template_name = "ui/cobranza/menu.html"

class CarteraVencidaListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/cobranza/cartera_vencida.html"
    context_object_name = "pagos"
    paginate_by = 30


    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "pdf":
            return self.export_pdf()

        return super().get(request, *args, **kwargs)

    def export_pdf(self):
        self.object_list = self.get_queryset()
        ctx = self.get_context_data(object_list=self.object_list)

        return render_to_pdf(
            "ui/cobranza/pdf/cartera_vencida_pdf.html",
            ctx,
            filename="cartera_vencida.pdf",
        )

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

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "pdf":
            return self.export_pdf()

        return super().get(request, *args, **kwargs)

    def export_pdf(self):
        self.object_list = self.get_queryset()
        ctx = self.get_context_data(object_list=self.object_list)

        return render_to_pdf(
            "ui/cobranza/pdf/pagos_por_vencer_pdf.html",
            ctx,
            filename="pagos_por_vencer.pdf",
        )

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


# Vista para enviar recordatorio manual

@login_required
@require_POST
def pago_enviar_recordatorio(request, pk):
    pago = get_object_or_404(
        Pago.objects.select_related("poliza", "cliente"),
        pk=pk,
    )

    if not can_manage_pago(request.user, pago):
        messages.error(request, "No tienes permisos para enviar recordatorios de este pago.")
        return redirect(request.META.get("HTTP_REFERER") or "ui:cartera_vencida")

    mensaje = registrar_recordatorio_pago(
        pago=pago,
        actor=request.user,
        canal="MANUAL",
    )

    messages.success(request, f"Recordatorio generado para el pago #{pago.id}.")
    request.session["ultimo_recordatorio"] = mensaje

    return redirect(request.META.get("HTTP_REFERER") or "ui:cartera_vencida")

@login_required
@require_POST
def pago_enviar_recordatorio_whatsapp(request, pk):
    pago = get_object_or_404(
        Pago.objects.select_related("poliza", "cliente"),
        pk=pk,
    )

    if not can_manage_pago(request.user, pago):
        messages.error(request, "No tienes permisos para enviar recordatorios de este pago.")
        return redirect(request.META.get("HTTP_REFERER") or "ui:cartera_vencida")

    categoria = "VENCIDO" if pago.estatus == Pago.Estatus.VENCIDO else "POR_VENCER"

    result = enviar_recordatorio_whatsapp(
        pago=pago,
        actor=request.user,
        categoria=categoria,
        dias=None,
    )

    if result.get("ok"):
        messages.success(request, f"Recordatorio por WhatsApp enviado para el pago #{pago.id}.")
    else:
        messages.error(
            request,
            f"No fue posible enviar el recordatorio por WhatsApp: {result.get('error') or result.get('data')}"
        )

    return redirect(request.META.get("HTTP_REFERER") or "ui:cartera_vencida")

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count, Value, DecimalField
from django.template.response import TemplateResponse
from django.utils.timezone import localdate
from django.views.generic import TemplateView
from django.utils.dateparse import parse_date

User = get_user_model()

class ReporteCobranzaAgenteView(LoginRequiredMixin, TemplateView):
    template_name = "ui/cobranza/reporte_cobranza_agente.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "pdf":
            return self.export_pdf()

        return super().get(request, *args, **kwargs)

    def export_pdf(self):
        ctx = self.get_context_data()

        ctx.update({
            "fecha_desde": ctx.get("fecha_desde"),
            "fecha_hasta": ctx.get("fecha_hasta"),
        })

        return render_to_pdf(
            "ui/cobranza/pdf/cobranza_agente_pdf.html",
            ctx,
            filename="cobranza_por_agente.pdf",
        )

    def _get_fechas(self):
        hoy = localdate()

        fecha_desde_raw = (self.request.GET.get("fecha_desde") or "").strip()
        fecha_hasta_raw = (self.request.GET.get("fecha_hasta") or "").strip()

        fecha_desde = parse_date(fecha_desde_raw) if fecha_desde_raw else hoy.replace(day=1)
        fecha_hasta = parse_date(fecha_hasta_raw) if fecha_hasta_raw else hoy

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

        return fecha_desde, fecha_hasta

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        fecha_desde, fecha_hasta = self._get_fechas()
        hoy = localdate()

        pagos = (
            Pago.objects
            .select_related("poliza", "poliza__agente")
            .filter(poliza__agente__isnull=False)
        )

        if not can_see_pagos(user):
            pagos = pagos.filter(poliza__agente=user)

        resumen = (
            pagos.values(
                "poliza__agente_id",
                "poliza__agente__username",
                "poliza__agente__first_name",
                "poliza__agente__last_name",
            )
            .annotate(
                cantidad_vencidos=Count(
                    "id",
                    filter=Q(
                        estatus=Pago.Estatus.VENCIDO,
                        fecha_vencimiento__isnull=False,
                        fecha_vencimiento__gte=fecha_desde,
                        fecha_vencimiento__lte=fecha_hasta,
                    ),
                ),
                monto_vencido=Coalesce(
                    Sum(
                        "monto",
                        filter=Q(
                            estatus=Pago.Estatus.VENCIDO,
                            fecha_vencimiento__isnull=False,
                            fecha_vencimiento__gte=fecha_desde,
                            fecha_vencimiento__lte=fecha_hasta,
                        ),
                    ),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                ),
                cantidad_por_vencer=Count(
                    "id",
                    filter=Q(
                        estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.PARCIAL],
                        fecha_vencimiento__isnull=False,
                        fecha_vencimiento__gte=fecha_desde,
                        fecha_vencimiento__lte=fecha_hasta,
                    ),
                ),
                monto_por_vencer=Coalesce(
                    Sum(
                        "monto",
                        filter=Q(
                            estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.PARCIAL],
                            fecha_vencimiento__isnull=False,
                            fecha_vencimiento__gte=fecha_desde,
                            fecha_vencimiento__lte=fecha_hasta,
                        ),
                    ),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                ),
                cantidad_cobrados=Count(
                    "id",
                    filter=Q(
                        estatus=Pago.Estatus.PAGADO,
                        fecha_pago__isnull=False,
                        fecha_pago__gte=fecha_desde,
                        fecha_pago__lte=fecha_hasta,
                    ),
                ),
                monto_cobrado=Coalesce(
                    Sum(
                        "monto_pagado",
                        filter=Q(
                            estatus=Pago.Estatus.PAGADO,
                            fecha_pago__isnull=False,
                            fecha_pago__gte=fecha_desde,
                            fecha_pago__lte=fecha_hasta,
                        ),
                    ),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                ),
                total_programado=Coalesce(
                    Sum("monto"),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                ),
            )
            .order_by("-monto_vencido", "poliza__agente__username")
        )

        filas = []
        for r in resumen:
            print("[reporteCobranzaAgenteView]-r[monto_cobrado]:",r["monto_cobrado"])
            nombre = " ".join(
                p for p in [
                    r.get("poliza__agente__first_name") or "",
                    r.get("poliza__agente__last_name") or "",
                ] if p.strip()
            ).strip()

            total_programado = r["total_programado"] or Decimal("0.00")
            monto_vencido = r["monto_vencido"] or Decimal("0.00")

            indice_morosidad = Decimal("0.00")
            if total_programado > 0:
                indice_morosidad = (monto_vencido / total_programado) * 100

            filas.append({
                "agente_id": r["poliza__agente_id"],
                "agente_nombre": nombre or r["poliza__agente__username"],
                "total_programado": total_programado,
                "cantidad_vencidos": r["cantidad_vencidos"],
                "monto_vencido": monto_vencido,
                "cantidad_por_vencer": r["cantidad_por_vencer"],
                "monto_por_vencer": r["monto_por_vencer"],
                "cantidad_cobrados": r["cantidad_cobrados"],
                "monto_cobrado": r["monto_cobrado"],
                "indice_morosidad": round(indice_morosidad, 2),
            })

        totales = {
            "cantidad_vencidos": sum(f["cantidad_vencidos"] for f in filas),
            "monto_vencido": sum((f["monto_vencido"] for f in filas), Decimal("0.00")),
            "cantidad_por_vencer": sum(f["cantidad_por_vencer"] for f in filas),
            "monto_por_vencer": sum((f["monto_por_vencer"] for f in filas), Decimal("0.00")),
            "cantidad_cobrados": sum(f["cantidad_cobrados"] for f in filas),
            "monto_cobrado": sum((f["monto_cobrado"] for f in filas), Decimal("0.00")),
        }

        ctx["reporte"] = filas
        ctx["totales"] = totales
        ctx["fecha_desde"] = fecha_desde
        ctx["fecha_hasta"] = fecha_hasta
        ctx["hoy"] = hoy
        return ctx

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.views.generic import ListView

User = get_user_model()


class ReporteCobranzaAgenteDetalleView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/cobranza/reporte_cobranza_agente_detalle.html"
    context_object_name = "pagos"
    paginate_by = 50

    def _get_fechas(self):
        hoy = localdate()
        fecha_desde_raw = (self.request.GET.get("fecha_desde") or "").strip()
        fecha_hasta_raw = (self.request.GET.get("fecha_hasta") or "").strip()

        fecha_desde = parse_date(fecha_desde_raw) if fecha_desde_raw else hoy.replace(day=1)
        fecha_hasta = parse_date(fecha_hasta_raw) if fecha_hasta_raw else hoy

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

        return fecha_desde, fecha_hasta

    def dispatch(self, request, *args, **kwargs):
        self.agente = get_object_or_404(User, pk=self.kwargs["agente_id"])

        if not can_see_pagos(request.user) and request.user != self.agente:
            return redirect("ui:reporte_cobranza_agente")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        fecha_desde, fecha_hasta = self._get_fechas()

        return (
            Pago.objects
            .select_related("poliza", "poliza__cliente", "poliza__aseguradora")
            .filter(
                poliza__agente=self.agente
            )
            .filter(
                Q(
                    estatus=Pago.Estatus.VENCIDO,
                    fecha_vencimiento__isnull=False,
                    fecha_vencimiento__gte=fecha_desde,
                    fecha_vencimiento__lte=fecha_hasta,
                )
                |
                Q(
                    estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.PARCIAL],
                    fecha_vencimiento__isnull=False,
                    fecha_vencimiento__gte=fecha_desde,
                    fecha_vencimiento__lte=fecha_hasta,
                )
                |
                Q(
                    estatus=Pago.Estatus.PAGADO,
                    fecha_pago__isnull=False,
                    fecha_pago__gte=fecha_desde,
                    fecha_pago__lte=fecha_hasta,
                )
            )
            .order_by("fecha_vencimiento", "id")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fecha_desde, fecha_hasta = self._get_fechas()
        ctx["agente"] = self.agente
        ctx["fecha_desde"] = fecha_desde
        ctx["fecha_hasta"] = fecha_hasta
        return ctx

from openpyxl import Workbook
from openpyxl.styles import Font
from django.http import HttpResponse


class ReporteCobranzaAgenteExcelView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        view = ReporteCobranzaAgenteView()
        view.request = request
        ctx = view.get_context_data()

        wb = Workbook()
        ws = wb.active
        ws.title = "Cobranza por Agente"

        headers = [
            "Agente",
            "Pagos vencidos",
            "Monto vencido",
            "Por vencer",
            "Monto por vencer",
            "Cobrados",
            "Monto cobrado",
            "Indice de Morosidad",
        ]
        ws.append(headers)

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for r in ctx["reporte"]:
            ws.append([
                r["agente_nombre"],
                r["cantidad_vencidos"],
                float(r["monto_vencido"]),
                r["cantidad_por_vencer"],
                float(r["monto_por_vencer"]),
                r["cantidad_cobrados"],
                float(r["monto_cobrado"]),
                r["indice_morosidad"],
            ])

        ws.append([
            "Totales",
            ctx["totales"]["cantidad_vencidos"],
            float(ctx["totales"]["monto_vencido"]),
            ctx["totales"]["cantidad_por_vencer"],
            float(ctx["totales"]["monto_por_vencer"]),
            ctx["totales"]["cantidad_cobrados"],
            float(ctx["totales"]["monto_cobrado"]),
        ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="reporte_cobranza_agente.xlsx"'

        wb.save(response)
        return response


class EstadoCuentaView(LoginRequiredMixin, TemplateView):
    template_name = "ui/cobranza/estado_cuenta.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "pdf":
            return self.export_pdf()

        return super().get(request, *args, **kwargs)

    def export_pdf(self):
        # Obtener contexto base del reporte
        ctx = self.get_context_data()

        # Agregar filtros al contexto
        ctx.update({
            "q": self.request.GET.get("q", "").strip(),
            "cliente_id": self.request.GET.get("cliente", "").strip(),
            "poliza_id": self.request.GET.get("poliza", "").strip(),
        })

        # Generar PDF
        return render_to_pdf(
            "ui/cobranza/pdf/estado_de_cuenta_pdf.html",
            ctx,
            filename="estado_cuenta.pdf",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        q = (self.request.GET.get("q") or "").strip()
        cliente_id = (self.request.GET.get("cliente") or "").strip()
        poliza_id = (self.request.GET.get("poliza") or "").strip()

        clientes = Cliente.objects.all().order_by("nombre")[:300]
        polizas = Poliza.objects.select_related("cliente", "aseguradora", "agente").order_by("-id")[:300]

        pagos = Pago.objects.select_related(
            "poliza",
            "poliza__cliente",
            "poliza__aseguradora",
            "poliza__agente",
        )

        if cliente_id:
            pagos = pagos.filter(poliza__cliente_id=cliente_id)

        if poliza_id:
            pagos = pagos.filter(poliza_id=poliza_id)

        if q:
            pagos = pagos.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(poliza__cliente__nombre__icontains=q) |
                Q(poliza__aseguradora__nombre__icontains=q) |
                Q(referencia__icontains=q)
            )

        pagos = pagos.order_by("fecha_vencimiento", "id")

        total_programado = pagos.aggregate(
            total=Coalesce(
                Sum("monto"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"]

        total_pagado = pagos.filter(
            estatus=Pago.Estatus.PAGADO
        ).aggregate(
            total=Coalesce(
                Sum("monto"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"]

        total_vencido = pagos.filter(
            estatus=Pago.Estatus.VENCIDO
        ).aggregate(
            total=Coalesce(
                Sum("monto"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"]

        total_pendiente = pagos.filter(
            estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.PARCIAL]
        ).aggregate(
            total=Coalesce(
                Sum("monto"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"]

        saldo = total_programado - total_pagado

        ctx["clientes"] = clientes
        ctx["polizas_select"] = polizas
        ctx["pagos"] = pagos

        ctx["q"] = q
        ctx["cliente_id"] = cliente_id
        ctx["poliza_id"] = poliza_id

        ctx["total_programado"] = total_programado
        ctx["total_pagado"] = total_pagado
        ctx["total_vencido"] = total_vencido
        ctx["total_pendiente"] = total_pendiente
        ctx["saldo"] = saldo
        ctx["total_registros"] = pagos.count()

        return ctx
   