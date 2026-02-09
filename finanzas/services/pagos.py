# Para crear el Plan de Pagos
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils.timezone import localdate

from finanzas.models import Pago
from polizas.models import Poliza


def _norm_forma_pago(fp: str) -> str:
    return (fp or "").strip().upper()


def crear_plan_pagos(poliza: Poliza, *, overwrite=False):
    """
    Crea pagos según poliza.forma_pago.
    Reglas:
      - CONTADO: 1 pago
      - MENSUAL: 12 pagos
      - TRIMESTRAL: 4 pagos
      - SEMESTRAL: 2 pagos

    Base de fechas:
      - inicia en vigencia_desde (si existe) o hoy.
    Montos:
      - distribuye prima_total en N pagos (redondeo a 2 decimales; ajusta el último).
    """
    fp = _norm_forma_pago(poliza.forma_pago)
    start = poliza.vigencia_desde or localdate()

    if fp in ("CONTADO",):
        n, step_days = 1, None
    elif fp in ("MENSUAL",):
        n, step_days = 12, 30
    elif fp in ("TRIMESTRAL",):
        n, step_days = 4, 90
    elif fp in ("SEMESTRAL",):
        n, step_days = 2, 182
    else:
        # fallback razonable
        n, step_days = 1, None

    with transaction.atomic():
        qs = Pago.objects.filter(poliza=poliza).exclude(estatus=Pago.Estatus.CANCELADO)

        if qs.exists():
            if not overwrite:
                return 0  # ya hay plan
            qs.delete()

        total = Decimal(poliza.prima_total or 0).quantize(Decimal("0.01"))
        if n == 0:
            return 0

        # monto base
        base = (total / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        created = 0
        sum_created = Decimal("0.00")

        for i in range(1, n + 1):
            if i < n:
                monto = base
                sum_created += monto
            else:
                # Ajuste final por redondeo
                monto = (total - sum_created).quantize(Decimal("0.01"))

            fecha = start if (step_days is None) else (start + timedelta(days=step_days * (i - 1)))

            Pago.objects.create(
                poliza=poliza,
                fecha_programada=fecha,
                monto=monto,
                estatus=Pago.Estatus.PENDIENTE,
                metodo="",
                referencia="",
            )
            created += 1

    return created
