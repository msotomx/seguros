from decimal import Decimal

from django.db.models import Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce

from finanzas.models import Pago


def estado_cuenta_por_poliza(poliza):
    pagos = (
        Pago.objects
        .filter(poliza=poliza)
        .order_by("fecha_programada", "id")
    )

    resumen = pagos.aggregate(
        total_programado=Coalesce(
            Sum("monto"),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
        total_pagado=Coalesce(
            Sum("monto_pagado", filter=Q(estatus=Pago.Estatus.PAGADO)),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
        total_vencido=Coalesce(
            Sum("monto", filter=Q(estatus=Pago.Estatus.VENCIDO)),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
        total_pendiente=Coalesce(
            Sum(
                "monto",
                filter=Q(estatus__in=[
                    Pago.Estatus.PENDIENTE,
                    Pago.Estatus.PARCIAL,
                    Pago.Estatus.EN_PROCESO,
                ])
            ),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
    )

    resumen["saldo"] = resumen["total_programado"] - resumen["total_pagado"]

    return {
        "pagos": pagos,
        "resumen": resumen,
    }


def estado_cuenta_por_cliente(cliente):
    pagos = (
        Pago.objects
        .filter(cliente=cliente)
        .select_related("poliza", "poliza__aseguradora")
        .order_by("fecha_programada", "id")
    )

    resumen = pagos.aggregate(
        total_programado=Coalesce(
            Sum("monto"),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
        total_pagado=Coalesce(
            Sum("monto_pagado", filter=Q(estatus=Pago.Estatus.PAGADO)),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
        total_vencido=Coalesce(
            Sum("monto", filter=Q(estatus=Pago.Estatus.VENCIDO)),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
        total_pendiente=Coalesce(
            Sum(
                "monto",
                filter=Q(estatus__in=[
                    Pago.Estatus.PENDIENTE,
                    Pago.Estatus.PARCIAL,
                    Pago.Estatus.EN_PROCESO,
                ])
            ),
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
    )

    resumen["saldo"] = resumen["total_programado"] - resumen["total_pagado"]

    return {
        "pagos": pagos,
        "resumen": resumen,
    }
