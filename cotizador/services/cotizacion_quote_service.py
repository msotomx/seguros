from __future__ import annotations

from typing import Any, Mapping

from cotizador.models import (
    Cotizacion,
    CotizacionProveedor,
)
from cotizador.services.provider_quote_service import (
    CotizacionProviderService,
)
from cotizador.services.quote_request_service import (
    QuoteRequestService,
)
from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.quotes.provider import QuoteProvider
from integrations.quotes.service import QuoteService


class CotizacionQuoteService:
    """
    Coordina el flujo completo de cotización del ERP.

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def quote_one(
        cls,
        *,
        cotizacion: Cotizacion,
        configuration: ProviderConfiguration,
        provider: QuoteProvider,
        package_code: str,
        garage: bool,
        request_json: Mapping[str, Any] | None = None,
        request_service=QuoteRequestService,
        provider_service_factory=CotizacionProviderService,
    ) -> CotizacionProveedor:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if provider.provider_code.strip().upper() != (
            configuration.provider.strip().upper()
        ):
            raise ValueError(
                "El provider no corresponde a la configuración."
            )

        request = request_service.build(
            cotizacion=cotizacion,
            provider_id=configuration.id,
            package_code=package_code,
            garage=garage,
        )

        quote_service = QuoteService(
            providers=[provider],
        )

        provider_service = provider_service_factory(
            quote_service=quote_service,
        )

        if request_json is None:
            request_json = request_service.to_dict(
                request
            )

        return provider_service.quote_one(
            cotizacion=cotizacion,
            provider_code=configuration.provider,
            request=request,
            request_json=request_json,
        )

