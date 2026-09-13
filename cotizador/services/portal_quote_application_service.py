from __future__ import annotations

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
)
from cotizador.services.cotizacion_quote_service import (
    CotizacionQuoteService,
)
from cotizador.services.provider_option_projection_service import (
    ProviderOptionProjectionService,
)
from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.quotes.provider import QuoteProvider


class PortalQuoteApplicationService:
    """
    Caso de uso de cotización utilizado por el Portal.

    Coordina:

    Cotizacion
        ↓
    CotizacionQuoteService
        ↓
    CotizacionProveedor
        ↓
    ProviderOptionProjectionService
        ↓
    CotizacionItem

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
        quote_service=CotizacionQuoteService,
        projection_service=ProviderOptionProjectionService,
    ) -> tuple[CotizacionItem, ...]:

        if not isinstance(
            cotizacion,
            Cotizacion,
        ):
            raise TypeError(
                "cotizacion debe ser una instancia "
                "de Cotizacion."
            )

        if not isinstance(
            configuration,
            ProviderConfiguration,
        ):
            raise TypeError(
                "configuration debe ser una instancia "
                "de ProviderConfiguration."
            )

        if (
            not isinstance(package_code, str)
            or not package_code.strip()
        ):
            raise ValueError(
                "package_code no puede estar vacío."
            )

        if not isinstance(garage, bool):
            raise TypeError(
                "garage debe ser booleano."
            )

        resultado_proveedor = quote_service.quote_one(
            cotizacion=cotizacion,
            configuration=configuration,
            provider=provider,
            package_code=package_code,
            garage=garage,
        )

        if not resultado_proveedor.success:
            return ()

        return projection_service.project(
            resultado_proveedor=resultado_proveedor,
            configuration=configuration,
        )
