from __future__ import annotations
from django.utils import timezone
from typing import Any, Optional, Dict
from django.db import transaction, IntegrityError
from polizas.models import PolizaEvento, Poliza


def generar_numero_poliza(aseguradora_id: int) -> str:
    # Provisional, pero suficientemente único por aseguradora:
    # POL-<aseg>-<YYYYMMDDHHMMSS>-<ms>
    now = timezone.now()
    return f"POL-{aseguradora_id}-{now:%Y%m%d%H%M%S}-{now.microsecond//1000:03d}"


def log_poliza_event(
    *,
    poliza: Poliza,
    tipo: str,
    actor=None,
    titulo: str = "",
    detalle: str = "",
    data: Optional[Dict[str, Any]] = None,
    dedupe_key: Optional[str] = None,
) -> Optional[PolizaEvento]:
    """
    Crea PolizaEvento con dedupe_key segura.

    - Si dedupe_key choca por UniqueConstraint, regresa None (idempotente).
    - No deja la transacción "rota" aunque estés dentro de un atomic mayor.
    """
    payload = dict(data or {})

    try:
        # Savepoint seguro si ya estás dentro de otra transacción.
        with transaction.atomic():
            evt = PolizaEvento.objects.create(
                poliza=poliza,
                tipo=tipo,
                titulo=titulo,
                detalle=detalle,
                data=payload or None,
                actor=actor,
                dedupe_key=dedupe_key,
            )
            return evt

    except IntegrityError:
        # Duplicate por uq(poliza,tipo,dedupe_key) => ya existe, no crear otro
        return None