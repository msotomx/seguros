from __future__ import annotations

from cotizador.models import Cotizacion
from cotizador.services.cotizacion_person_service import (
    CotizacionPersonService,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.persons.contracts import PersonResult
from integrations.persons.provider_resolver_factory import (
    build_person_provider_resolver,
)


class PortalPersonApplicationService:
    """
    Caso de uso para crear la persona asegurada
    en el provider seleccionado.

    Coordina:

    Cotizacion
        ↓
    ProviderConfiguration
        ↓
    PersonProviderResolver
        ↓
    CotizacionPersonService
        ↓
    PersonResult

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def create_one(
        cls,
        *,
        cotizacion: Cotizacion,
        provider_code: str,
        ambiente: str,
        ramo: str,
        configuration_service=ProviderConfigurationService,
        resolver_factory=build_person_provider_resolver,
        person_service=CotizacionPersonService,
    ) -> PersonResult:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia "
                "de Cotizacion."
            )

        if (
            not isinstance(provider_code, str)
            or not provider_code.strip()
        ):
            raise ValueError(
                "provider_code no puede estar vacío."
            )

        if (
            not isinstance(ambiente, str)
            or not ambiente.strip()
        ):
            raise ValueError(
                "ambiente no puede estar vacío."
            )

        if (
            not isinstance(ramo, str)
            or not ramo.strip()
        ):
            raise ValueError(
                "ramo no puede estar vacío."
            )

        configuration = configuration_service.get_active(
            provider=provider_code,
            ambiente=ambiente,
            ramo=ramo,
        )

        resolver = resolver_factory()

        provider = resolver.build(
            provider_code=configuration.provider,
            ambiente=configuration.ambiente,
            ramo=configuration.ramo,
        )

        return person_service.create_one(
            cotizacion=cotizacion,
            configuration=configuration,
            provider=provider,
        )
