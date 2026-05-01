from __future__ import annotations

from datetime import date
from django.db.models import Count, Sum, Q
from django.utils import timezone

from cotizador.models import Cotizacion
from polizas.models import Poliza
from finanzas.models import Pago, Comision
from datetime import timedelta


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

def calcular_indice_morosidad(total_programado, total_vencido):
    if not total_programado or total_programado == 0:
        return Decimal("0.00")
    return (total_vencido / total_programado) * 100


from decimal import Decimal
from django.db.models.functions import Coalesce
from django.db.models import Value, DecimalField


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

    # Todos los pagos del agente
    pagos_agente = Pago.objects.filter(poliza__agente=user)

    total_programado = pagos_agente.aggregate(
        total=Coalesce(
            Sum("monto"),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
    )["total"]

    total_vencido = pagos_agente.aggregate(
        total=Coalesce(
            Sum("monto", filter=Q(estatus=Pago.Estatus.VENCIDO)),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
    )["total"]

    # KPI índice de morosidad
    if total_programado > 0:
        indice_morosidad = (total_vencido / total_programado) * 100
    else:
        indice_morosidad = Decimal("0.00")

    # Comisiones pendientes (monto)
    comisiones_pendientes = Comision.objects.filter(
        agente=user,
        estatus=Comision.Estatus.PENDIENTE,
    )
    comisiones_pagadas_mes = Comision.objects.filter(
        agente=user,
        estatus=Comision.Estatus.PAGADA,
        fecha_pago__gte=start_m,
        fecha_pago__lt=end_m,
    )
    ultimas_comisiones = (
        Comision.objects
        .filter(agente=user)
        .select_related("poliza", "poliza__cliente")
        .order_by("-fecha_generacion", "-id")[:8]
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

            # Comisiones
            "comisiones_pendientes": comisiones_pendientes.count(),
            "comisiones_pagadas_mes": comisiones_pagadas_mes.count(),
        },
        "money": {
            "comisiones_pendiente_total": comisiones_pendientes.aggregate(
                total=Coalesce(
                    Sum("monto_comision"),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                )
            )["total"],

            "comisiones_pagadas_mes_total": comisiones_pagadas_mes.aggregate(
                total=Coalesce(
                    Sum("monto_comision"),
                    Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                )
            )["total"],

            "total_programado": total_programado,
            "monto_vencido": total_vencido,
        },
        "rates": {
            "conversion_pct": round(conversion_pct, 2),
            "indice_morosidad": round(indice_morosidad, 2),
        },
        "lists": {
            "ult_cot": ult_cot,
            "pol_por_vencer": pol_por_vencer.select_related("cliente", "aseguradora")[:8],
            "ultimas_comisiones": ultimas_comisiones,
        },
        "breakdown": breakdown_map,
    }


from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Value, DecimalField, Q
from django.db.models.functions import Coalesce
from django.utils.timezone import localdate

from finanzas.models import Pago
from ui.services.perms import can_see_pagos


def queryset_pagos_dashboard(user):
    qs = Pago.objects.select_related("poliza", "poliza__agente")

    if can_see_pagos(user):
        return qs

    return qs.filter(poliza__agente=user)


def obtener_kpis_cobranza(user):
    hoy = localdate()
    inicio_mes = hoy.replace(day=1)
    limite_7 = hoy + timedelta(days=7)

    qs = queryset_pagos_dashboard(user)

    vencidos = qs.filter(estatus=Pago.Estatus.VENCIDO)
    por_vencer = qs.filter(
        estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.PARCIAL],
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=limite_7,
    )
    cobrados_mes = qs.filter(
        estatus=Pago.Estatus.PAGADO,
        fecha_pago__isnull=False,
        fecha_pago__gte=inicio_mes,
        fecha_pago__lte=hoy,
    )

    kpi = {
        "cantidad_vencidos": vencidos.count(),
        "monto_vencido": vencidos.aggregate(
            total=Coalesce(
                Sum("monto"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"],
        "cantidad_por_vencer": por_vencer.count(),
        "monto_por_vencer": por_vencer.aggregate(
            total=Coalesce(
                Sum("monto"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"],
        "cantidad_cobrados_mes": cobrados_mes.count(),
        "monto_cobrado_mes": cobrados_mes.aggregate(
            total=Coalesce(
                Sum("monto_pagado"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
        )["total"],
    }

    return kpi
