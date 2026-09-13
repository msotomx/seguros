from __future__ import annotations

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
)
from cotizador.services.portal_quote_application_service import (
    PortalQuoteApplicationService,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.quotes.provider_resolver_factory import (
    build_quote_provider_resolver,
)
from integrations.catalog.quote_package_service import (
    QuotePackageService,
)


class PortalMultiProviderQuoteService:
    """
    Ejecuta una cotización contra todos los providers
    activos y habilitados para cotizar.

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def quote(
        cls,
        *,
        cotizacion: Cotizacion,
        ambiente: str,
        ramo: str,
        configuration_service=ProviderConfigurationService,
        package_service=QuotePackageService,
        resolver_factory=build_quote_provider_resolver,
        application_service=PortalQuoteApplicationService,
    ) -> tuple[CotizacionItem, ...]:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia "
                "de Cotizacion."
            )

        if not isinstance(ambiente, str) or not ambiente.strip():
            raise ValueError(
                "ambiente no puede estar vacío."
            )

        if not isinstance(ramo, str) or not ramo.strip():
            raise ValueError(
                "ramo no puede estar vacío."
            )

        configurations = (
            configuration_service.list_active_for_quote(
                ambiente=ambiente,
                ramo=ramo,
            )
        )

        resolver = resolver_factory()

        items: list[CotizacionItem] = []

        for configuration in configurations:
            provider = resolver.build(
                provider_code=configuration.provider,
                ambiente=configuration.ambiente,
                ramo=configuration.ramo,
            )

            garage = configuration.settings.get(
                "GARAGE_USE",
                False,
            )

            if not isinstance(garage, bool):
                raise ValueError(
                    "GARAGE_USE debe ser booleano."
                )

            package_codes = (
                package_service.list_internal_codes_for_provider(
                    provider_id=configuration.id,
                )
            )

            for package_code in package_codes:
                provider_items = application_service.quote_one(
                    cotizacion=cotizacion,
                    configuration=configuration,
                    provider=provider,
                    package_code=package_code,
                    garage=garage,
                )

                items.extend(provider_items)

        return tuple(items)
