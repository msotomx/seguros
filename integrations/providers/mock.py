# integrations/providers/mock.py
# MockProvider
# Este provider va a “pagar” un Pago buscándolo por id o referencia.
from __future__ import annotations

from typing import Any, Dict
from django.utils import timezone

from integrations.providers.base import BaseProvider
from finanzas.models import Pago
from polizas.models import PolizaEvento
from polizas.services import log_poliza_event


class MockProvider(BaseProvider):
    slug = "mock"

    def validate_signature(self, request, raw_body: bytes) -> bool:
        return True

    def normalize_event(self, payload: Dict[str, Any], request=None) -> Dict[str, Any]:
        """
        Payload esperado ejemplo:
        {
          "id": "evt_123",             # opcional
          "type": "payment.succeeded", # opcional
          "action": "PAYMENT_SUCCEEDED",
          "data": {"pago_id": 10, "referencia": "ABC"}
        }
        """
        event_id = payload.get("id") or ""
        event_type = payload.get("type") or payload.get("event_type") or ""
        action = payload.get("action") or ""
        data = payload.get("data") or {}

        return {
            "event_id": event_id,
            "event_type": event_type,
            "action": action,
            "data": data,
        }

    def process(self, normalized: Dict[str, Any]) -> None:
        action = normalized.get("action", "")
        data = normalized.get("data") or {}

        if action == "PAYMENT_SUCCEEDED":
            self._payment_succeeded(data)
            return

        if action == "PAYMENT_FAILED":
            # opcional: aquí marcarías algo o registrarías
            return

        # acciones desconocidas -> no hacemos nada (podrías levantar excepción si prefieres)
        return

    def _payment_succeeded(self, data: Dict[str, Any]) -> None:
        pago_id = data.get("pago_id")
        if not pago_id:
            raise ValueError("mock: missing data.pago_id")

        pago = Pago.objects.select_related("poliza").get(id=pago_id)

        # Idempotencia de negocio: si ya está PAGADO, no vuelvas a tocar
        if pago.estatus == Pago.Estatus.PAGADO:
            # Aún así, intentamos log con dedupe (no duplica)
            log_poliza_event(
                poliza=pago.poliza,
                tipo=PolizaEvento.Tipo.PAGO_PAGADO,
                actor=None,
                titulo="Pago marcado como pagado (mock)",
                data={"pago_id": pago.id, "monto": str(pago.monto)},
                dedupe_key=f"PAGO_PAGADO:{pago.id}",
            )
            return

        pago.estatus = Pago.Estatus.PAGADO
        pago.fecha_pago = timezone.localdate()
        pago.referencia = str(data.get("referencia") or pago.referencia or "")
        pago.metodo = str(data.get("metodo") or pago.metodo or "MOCK")

        pago.save(update_fields=["estatus", "fecha_pago", "referencia", "metodo", "updated_at"])

        log_poliza_event(
            poliza=pago.poliza,
            tipo=PolizaEvento.Tipo.PAGO_PAGADO,
            actor=None,
            titulo="Pago marcado como pagado",
            data={
                "pago_id": pago.id,
                "monto": str(pago.monto),
                "metodo": pago.metodo,
                "referencia": pago.referencia,
            },
            dedupe_key=f"PAGO_PAGADO:{pago.id}",
        )
