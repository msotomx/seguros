from __future__ import annotations

from typing import Any, Mapping

from cotizador.models import (
    Cotizacion,
    CotizacionProveedor,
)
from cotizador.services.quote_persistence_service import (
    QuotePersistenceService,
)
from integrations.quotes.contracts import (
    QuoteAttempt,
    QuoteResult,
)


class QuoteReconciliationService:
    """
    Persiste una cotización previamente recuperada
    desde un proveedor.

    No ejecuta una nueva cotización.
    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def persist_result(
        cls,
        *,
        cotizacion: Cotizacion,
        result: QuoteResult,
        elapsed_ms: int = 0,
        request_json: Mapping[str, Any] | None = None,
        persistence_service=QuotePersistenceService,
    ) -> CotizacionProveedor:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if not isinstance(result, QuoteResult):
            raise TypeError(
                "result debe ser una instancia de QuoteResult."
            )

        if (
            not isinstance(elapsed_ms, int)
            or isinstance(elapsed_ms, bool)
            or elapsed_ms < 0
        ):
            raise ValueError(
                "elapsed_ms debe ser un entero cero o mayor."
            )

        attempt = QuoteAttempt(
            provider_code=result.provider_code,
            success=True,
            elapsed_ms=elapsed_ms,
            result=result,
        )

        return persistence_service.persist(
            cotizacion=cotizacion,
            attempt=attempt,
            request_json=request_json,
        )
