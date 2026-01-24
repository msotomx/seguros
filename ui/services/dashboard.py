from __future__ import annotations

from datetime import date
from django.db.models import Count, Sum, Q
from django.utils import timezone

from cotizador.models import Cotizacion
from polizas.models import Poliza
from finanzas.models import Pago, Comision


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
        },
        "breakdown": breakdown_map,
    }
