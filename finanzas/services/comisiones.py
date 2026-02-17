from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction

from finanzas.models import Comision
from polizas.models import Poliza

DEFAULT_PCT = Decimal("10.0")  # 10% (cámbialo cuando quieras)

def crear_comision_poliza(poliza: Poliza, *, porcentaje: Decimal | None = None, overwrite=False) -> Comision | None:
    """
    Crea comisión PENDIENTE para la póliza.
    - Si ya existe y overwrite=False, no hace nada.
    - Usa poliza.agente como agente de comisión.
    - Monto = prima_total * porcentaje/100
    """
    if not poliza.agente_id:
        return None

    pct = (porcentaje if porcentaje is not None else DEFAULT_PCT)

    with transaction.atomic():
        qs = Comision.objects.filter(poliza=poliza, agente_id=poliza.agente_id)

        if qs.exists():
            if not overwrite:
                return qs.order_by("-created_at").first()
            qs.delete()

        prima = Decimal(poliza.prima_total or 0)
        monto = (prima * (pct / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return Comision.objects.create(
            poliza=poliza,
            agente_id=poliza.agente_id,
            porcentaje=pct,
            monto=monto,
            estatus=Comision.Estatus.PENDIENTE,
        )
