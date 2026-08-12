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
    InternalQuoteRequest,
)
from integrations.quotes.service import QuoteService


class CotizacionProviderService:
    """
    Coordina la ejecución de una cotización contra un proveedor
    y persiste el QuoteAttempt resultante.

    No conoce implementaciones específicas de aseguradoras.
    """

    def __init__(
        self,
        *,
        quote_service: QuoteService,
        persistence_service=QuotePersistenceService,
    ) -> None:
        if not isinstance(quote_service, QuoteService):
            raise TypeError(
                "quote_service debe ser una instancia de QuoteService."
            )

        self.quote_service = quote_service
        self.persistence_service = persistence_service

    def quote_one(
        self,
        *,
        cotizacion: Cotizacion,
        provider_code: str,
        request: InternalQuoteRequest,
        request_json: Mapping[str, Any] | None = None,
    ) -> CotizacionProveedor:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if not isinstance(request, InternalQuoteRequest):
            raise TypeError(
                "request debe ser una instancia de "
                "InternalQuoteRequest."
            )

        attempt = self.quote_service.quote_one(
            provider_code,
            request,
        )

        return self.persistence_service.persist(
            cotizacion=cotizacion,
            attempt=attempt,
            request_json=request_json,
        )
