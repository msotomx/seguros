from __future__ import annotations

from cotizador.services.person_request_service import (
    PersonRequestService,
)
from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.persons.contracts import PersonResult
from integrations.persons.provider import PersonProvider
from integrations.persons.service import PersonService
from cotizador.models import (
    Cotizacion,
    CotizacionProveedorPersona,
)
from cotizador.services.person_persistence_service import (
    PersonPersistenceService,
)


class CotizacionPersonService:
    """
    Coordina Create Person para una Cotizacion.

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def create_one(
        cls,
        *,
        cotizacion: Cotizacion,
        configuration: ProviderConfiguration,
        provider: PersonProvider,
        request_service=PersonRequestService,
        person_service_factory=PersonService,
        persistence_service=PersonPersistenceService,
    ) -> PersonResult:

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
        )

        person_service = person_service_factory(
            providers=[provider],
        )

        result = person_service.create_one(
            provider_code=configuration.provider,
            request=request,
        )

        persistence_service.save(
            cotizacion=cotizacion,
            person_result=result,
            rol=CotizacionProveedorPersona.Rol.ASEGURADO,
        )

        return result
