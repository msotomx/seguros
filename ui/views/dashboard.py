from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from datetime import date
from django.views.generic import TemplateView

from crm.models import Cliente
from cotizador.models import Cotizacion
from finanzas.models import Pago, Comision
from polizas.models import Poliza, PolizaEvento


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_internal(user) -> bool:
    if not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name__in=["Admin", "Supervisor", "Agente"]).exists()
    )

def month_range(today: date | None = None):
    """Regresa (inicio_mes, fin_mes_exclusivo)."""
    today = today or timezone.localdate()
    start = today.replace(day=1)
    # siguiente mes
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def agente_kpis(user):
    """
    KPIs para agente (owner/agente).
    Basado en:
      - Cotizacion.owner
      - Poliza.agente
      - Pago.poliza
      - Comision.agente
    """
    today = timezone.localdate()
    start_m, end_m = month_range(today)

    # Cotizaciones del agente (mes)
    cot_mes = Cotizacion.objects.filter(owner=user, created_at__date__gte=start_m, created_at__date__lt=end_m)

    # Pendientes: BORRADOR + ENVIADA (en general)
    cot_pendientes = Cotizacion.objects.filter(
        owner=user,
        estatus__in=[Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA],
    )

    # Pólizas del agente
    polizas = Poliza.objects.filter(agente=user)
    pol_vigentes = polizas.filter(
        estatus=Poliza.Estatus.VIGENTE,
        vigencia_desde__lte=today,
        vigencia_hasta__gte=today,
    )

    in_30 = today + timedelta(days=30)
    pol_por_vencer = polizas.filter(
        estatus=Poliza.Estatus.VIGENTE,
        vigencia_hasta__gte=today,
        vigencia_hasta__lte=in_30,
    ).order_by("vigencia_hasta")

    # Pólizas emitidas este mes (para conversión)
    pol_mes = polizas.filter(created_at__date__gte=start_m, created_at__date__lt=end_m)

    # Conversión (aprox práctica):
    # pólizas del mes / cotizaciones del mes
    cot_mes_count = cot_mes.count()
    pol_mes_count = pol_mes.count()
    conversion_pct = (pol_mes_count / cot_mes_count * 100) if cot_mes_count else 0

    # Pagos vencidos de pólizas del agente
    pagos_vencidos = Pago.objects.filter(
        poliza__agente=user,
        estatus=Pago.Estatus.VENCIDO,
    )

    # Comisiones pendientes (monto)
    com_pendientes = Comision.objects.filter(
        agente=user,
        estatus=Comision.Estatus.PENDIENTE,
    )

    # Top: últimas cotizaciones (para “trabajo del día”)
    ult_cot = (
        Cotizacion.objects
        .filter(owner=user)
        .select_related("cliente", "vehiculo", "flotilla")
        .order_by("-created_at")[:8]
    )

    # Pendientes por estatus (mini breakdown)
    breakdown = (
        Cotizacion.objects
        .filter(owner=user)
        .values("estatus")
        .annotate(total=Count("id"))
        .order_by()
    )
    breakdown_map = {row["estatus"]: row["total"] for row in breakdown}

    return {
        "period": {"start": start_m, "end": end_m},
        "counts": {
            "cot_mes": cot_mes_count,
            "cot_pendientes": cot_pendientes.count(),
            "pol_vigentes": pol_vigentes.count(),
            "pol_por_vencer": pol_por_vencer.count(),
            "pagos_vencidos": pagos_vencidos.count(),
        },
        "money": {
            "com_pendiente_total": com_pendientes.aggregate(s=Sum("monto"))["s"] or 0,
        },
        "rates": {
            "conversion_pct": round(conversion_pct, 2),
        },
        "lists": {
            "ult_cot": ult_cot,
            "pol_por_vencer": pol_por_vencer.select_related("cliente", "aseguradora")[:8],
        },
        "breakdown": breakdown_map,
    }


# ---------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------

class InternalRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_internal(self.request.user)


class SupervisorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return (
            u.is_authenticated and (
                u.is_superuser
                or u.is_staff
                or u.groups.filter(name__in=["Supervisor", "Admin"]).exists()
            )
        )

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_superuser or u.groups.filter(name="Admin").exists())


# ---------------------------------------------------------------------
# 1) Router principal
# ---------------------------------------------------------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    /ui/  -> redirige según rol
    """
    template_name = "ui/dashboard/basic.html"

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not is_internal(user):
            return redirect("portal:dashboard")

        if user.is_superuser or user_in_group(user, "Admin"):
            return redirect("ui:dashboard_admin")

        if user_in_group(user, "Supervisor"):
            return redirect("ui:dashboard_supervisor")

        if user_in_group(user, "Agente"):
            return redirect("ui:dashboard_agente")

        return redirect("ui:dashboard_basic")


# ---------------------------------------------------------------------
# 2) Dashboard básico / fallback
# ---------------------------------------------------------------------

class BasicDashboardView(LoginRequiredMixin, InternalRequiredMixin, TemplateView):
    template_name = "ui/dashboard/basic.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx


# ---------------------------------------------------------------------
# 3) Dashboard Agente
# ---------------------------------------------------------------------

from ui.services.dashboard import obtener_kpis_cobranza

class AgenteDashboardView(LoginRequiredMixin, InternalRequiredMixin, TemplateView):
    template_name = "ui/dashboard/agente.html"

    def dispatch(self, request, *args, **kwargs):
        if not (user_in_group(request.user, "Agente") or request.user.is_superuser or user_in_group(request.user, "Admin")):
            return redirect("ui:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        ctx["kpi"] = agente_kpis(user)
        ctx["kpis_cobranza"] = obtener_kpis_cobranza(user)
        ctx["ultimas_polizas"] = (
            Poliza.objects
            .filter(agente=user)
            .select_related("cliente", "aseguradora")
            .order_by("-id")[:10]
        )

        ctx["proximos_pagos"] = (
            Pago.objects
            .filter(poliza__agente=user, estatus=Pago.Estatus.PENDIENTE)
            .select_related("poliza", "poliza__cliente")
            .order_by("fecha_programada", "id")[:10]
        )

        ctx["today"] = today
        return ctx


# ---------------------------------------------------------------------
# 4) Dashboard Supervisor
# ---------------------------------------------------------------------

from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from crm.models import Cliente
from finanzas.models import Pago, Comision
from polizas.models import Poliza, PolizaEvento


class SupervisorDashboardView(LoginRequiredMixin, SupervisorRequiredMixin, TemplateView):
    template_name = "ui/dashboard/supervisor.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        today = timezone.localdate()
        last_7 = today - timedelta(days=7)
        last_30 = today - timedelta(days=30)
        next_7 = today + timedelta(days=7)
        next_30 = today + timedelta(days=30)

        polizas = Poliza.objects.all()
        pagos = Pago.objects.all()
        comisiones = Comision.objects.all()

        ctx["today"] = today

        # KPIs pólizas
        ctx["polizas_kpi"] = {
            "vigentes": polizas.filter(estatus=Poliza.Estatus.VIGENTE).count(),
            "vencidas": polizas.filter(estatus=Poliza.Estatus.VENCIDA).count(),
            "canceladas": polizas.filter(estatus=Poliza.Estatus.CANCELADA).count(),
            "en_proceso": polizas.filter(estatus=Poliza.Estatus.EN_PROCESO).count(),
            "por_vencer_30d": polizas.filter(
                estatus=Poliza.Estatus.VIGENTE,
                vigencia_hasta__gte=today,
                vigencia_hasta__lte=next_30,
            ).count(),
        }

        # KPIs pagos
        ctx["pagos_kpi"] = {
            "pendientes": pagos.filter(estatus=Pago.Estatus.PENDIENTE).count(),
            "vencidos": pagos.filter(estatus=Pago.Estatus.VENCIDO).count(),
            "pagados": pagos.filter(estatus=Pago.Estatus.PAGADO).count(),
            "cancelados": pagos.filter(estatus=Pago.Estatus.CANCELADO).count(),
            "monto_pendiente": pagos.filter(
                estatus=Pago.Estatus.PENDIENTE
            ).aggregate(s=Sum("monto"))["s"] or 0,
            "monto_vencido": pagos.filter(
                estatus=Pago.Estatus.VENCIDO
            ).aggregate(s=Sum("monto"))["s"] or 0,
            "monto_pagado_30d": pagos.filter(
                estatus=Pago.Estatus.PAGADO,
                fecha_pago__gte=last_30,
            ).aggregate(s=Sum("monto"))["s"] or 0,
            "pagos_pagados_30d": pagos.filter(
                estatus=Pago.Estatus.PAGADO,
                fecha_pago__gte=last_30,
            ).count(),
    }


        # KPIs clientes/comisiones
        ctx["clientes_kpi"] = {
            "total": Cliente.objects.count(),
            "nuevos_30d": Cliente.objects.filter(created_at__date__gte=last_30).count()
            if hasattr(Cliente, "created_at") else None,
        }

        ctx["comisiones_kpi"] = {
            "pendientes": comisiones.filter(estatus=Comision.Estatus.PENDIENTE).count(),
            "pagadas": comisiones.filter(estatus=Comision.Estatus.PAGADA).count(),
            "monto_pendiente": comisiones.filter(
                estatus=Comision.Estatus.PENDIENTE
            ).aggregate(s=Sum("monto"))["s"] or 0,
        }

        # Eventos recientes
        ctx["eventos"] = (
            PolizaEvento.objects
            .select_related("poliza", "actor")
            .order_by("-created_at", "-id")[:20]
        )

        # Resumen actividad 7 días
        ctx["eventos_7d"] = list(
            PolizaEvento.objects
            .filter(created_at__date__gte=last_7)
            .values("tipo")
            .annotate(total=Count("id"))
            .order_by("-total")
        )

        # Pagos próximos a vencer
        ctx["proximos_pagos"] = (
            Pago.objects
            .select_related("poliza", "poliza__cliente")
            .filter(
                estatus=Pago.Estatus.PENDIENTE,
                fecha_programada__gte=today,
                fecha_programada__lte=next_7,
            )
            .order_by("fecha_programada", "id")[:15]
        )

        # Pólizas próximas a vencer
        ctx["proximas_polizas"] = (
            Poliza.objects
            .select_related("cliente", "aseguradora", "agente")
            .filter(
                estatus=Poliza.Estatus.VIGENTE,
                vigencia_hasta__gte=today,
                vigencia_hasta__lte=next_30,
            )
            .order_by("vigencia_hasta", "id")[:15]
        )

        # Últimas pólizas
        ctx["ultimas_polizas"] = (
            Poliza.objects
            .select_related("cliente", "aseguradora", "agente")
            .order_by("-id")[:10]
        )

        return ctx


# ---------------------------------------------------------------------
# 5) Dashboard Admin
# ---------------------------------------------------------------------

from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from crm.models import Cliente
from finanzas.models import Pago, Comision
from polizas.models import Poliza, PolizaEvento

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = "ui/dashboard/admin.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        today = timezone.localdate()
        last_7 = today - timedelta(days=7)
        last_30 = today - timedelta(days=30)
        next_30 = today + timedelta(days=30)

        polizas = Poliza.objects.all()
        pagos = Pago.objects.all()
        comisiones = Comision.objects.all()

        ctx["today"] = today

        # KPIs globales
        pagos_30d = pagos.filter(
            estatus=Pago.Estatus.PAGADO,
            fecha_pago__gte=last_30,
        )

        ctx["kpi_global"] = {
            "clientes_total": Cliente.objects.count(),
            "polizas_total": polizas.count(),
            "polizas_vigentes": polizas.filter(estatus=Poliza.Estatus.VIGENTE).count(),
            "polizas_en_proceso": polizas.filter(estatus=Poliza.Estatus.EN_PROCESO).count(),
            "polizas_vencidas": polizas.filter(estatus=Poliza.Estatus.VENCIDA).count(),
            "polizas_canceladas": polizas.filter(estatus=Poliza.Estatus.CANCELADA).count(),
            "pagos_pendientes": pagos.filter(estatus=Pago.Estatus.PENDIENTE).count(),
            "pagos_vencidos": pagos.filter(estatus=Pago.Estatus.VENCIDO).count(),
            "pagos_pagados": pagos.filter(estatus=Pago.Estatus.PAGADO).count(),
            "monto_pendiente": pagos.filter(
                estatus=Pago.Estatus.PENDIENTE
            ).aggregate(s=Sum("monto"))["s"] or 0,
            "monto_vencido": pagos.filter(
                estatus=Pago.Estatus.VENCIDO
            ).aggregate(s=Sum("monto"))["s"] or 0,
            "monto_pagado_30d": pagos_30d.aggregate(s=Sum("monto"))["s"] or 0,
            "pagos_pagados_30d": pagos_30d.count(),
            "comisiones_pendientes": comisiones.filter(
                estatus=Comision.Estatus.PENDIENTE
            ).count(),
            "monto_comisiones_pendientes": comisiones.filter(
                estatus=Comision.Estatus.PENDIENTE
            ).aggregate(s=Sum("monto"))["s"] or 0,
        }

        # Pólizas próximas a vencer
        ctx["proximas_polizas"] = (
            Poliza.objects
            .select_related("cliente", "aseguradora", "agente")
            .filter(
                estatus=Poliza.Estatus.VIGENTE,
                vigencia_hasta__gte=today,
                vigencia_hasta__lte=next_30,
            )
            .order_by("vigencia_hasta", "id")[:15]
        )

        # Últimos pagos registrados
        ctx["ultimos_pagos"] = (
            Pago.objects
            .select_related("poliza", "poliza__cliente")
            .order_by("-id")[:15]
        )

        # Últimas pólizas
        ctx["ultimas_polizas"] = (
            Poliza.objects
            .select_related("cliente", "aseguradora", "agente")
            .order_by("-id")[:12]
        )

        # Actividad reciente
        ctx["ultimos_eventos"] = (
            PolizaEvento.objects
            .select_related("poliza", "actor")
            .order_by("-created_at", "-id")[:20]
        )

        # Resumen actividad 7 días
        ctx["eventos_7d"] = list(
            PolizaEvento.objects
            .filter(created_at__date__gte=last_7)
            .values("tipo")
            .annotate(total=Count("id"))
            .order_by("-total")
        )

        return ctx
