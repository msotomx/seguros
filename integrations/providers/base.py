from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional


class BaseProvider:
    slug: str = ""

    def validate_signature(self, request, raw_body: bytes) -> bool:
        """
        Valida firma del webhook. Por defecto: True (útil para mock/dev).
        En providers reales: implementar HMAC/firmas.
        """
        return True

    def normalize_event(self, payload: Dict[str, Any], request=None) -> Dict[str, Any]:
        """
        Debe regresar dict con:
          - event_id (str)
          - event_type (str)
          - action (str)
          - data (dict)
        """
        raise NotImplementedError

    def process(self, normalized: Dict[str, Any]) -> None:
        """
        Aplica efectos en el sistema (Pago/Poliza/PolizaEvento).
        """
        raise NotImplementedError

    def fallback_event_id(self, raw_body: bytes, payload: Optional[Dict[str, Any]] = None, request=None) -> str:
        """
        Si el provider no manda event_id confiable, generamos uno determinístico.
        """
        h = hashlib.sha256(raw_body or b"").hexdigest()
        return f"bodysha256:{h}"
    