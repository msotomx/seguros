from __future__ import annotations
import logging

from cotizador.services.issue_request_service import (
    IssueRequestService,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.issues.provider_resolver_factory import (
    build_issue_provider_resolver,
)
from integrations.issues.service import IssueService
from integrations.persons.provider_resolver_factory import (
    build_person_provider_resolver,
)
from cotizador.services.issue_persistence_service import (
    IssuePersistenceService,
)
from cotizador.services.issue_attempt_persistence_service import (
    IssueAttemptPersistenceService,
)
from polizas.models import Poliza
from cotizador.models import (
    CotizacionItem,
    CotizacionProveedorEmision,
    CotizacionProveedorPersona,
)
from cotizador.services.cotizacion_person_service import (
    CotizacionPersonService,
)

logger = logging.getLogger(__name__)

class PortalIssueApplicationService:
    """
    Caso de uso para emitir un CotizacionItem.

    Coordina:

    CotizacionItem
        ↓
    ProviderConfiguration
        ↓
    IssueProviderResolver
        ↓
    IssueRequestService
        ↓
    IssueService
        ↓
    IssueResult

    Persiste la póliza después de una emisión exitosa.
    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def issue_one(
        cls,
        *,
        cotizacion_item: CotizacionItem,
        configuration_service=ProviderConfigurationService,
        resolver_factory=build_issue_provider_resolver,
        request_service=IssueRequestService,
        issue_service_factory=IssueService,
        persistence_service=IssuePersistenceService,
        attempt_persistence_service=IssueAttemptPersistenceService,
        person_resolver_factory=build_person_provider_resolver,
        person_service=CotizacionPersonService,
    ) -> Poliza:
        if not isinstance(
            cotizacion_item,
            CotizacionItem,
        ):
            raise TypeError(
                "cotizacion_item debe ser una instancia "
                "de CotizacionItem."
            )
        provider_option = cotizacion_item.provider_option

        if provider_option is None:
            raise ValueError(
                "El CotizacionItem no tiene opción de proveedor."
            )

        quote_attempt = provider_option.cotizacion_proveedor

        configuration_id = (
            quote_attempt.provider_configuration_id
        )

        if not configuration_id:
            raise ValueError(
                "La cotización del proveedor no tiene "
                "provider_configuration_id."
            )

        provider_code = (
            cotizacion_item.provider or ""
        ).strip().upper()

        if not provider_code:
            raise ValueError(
                "El CotizacionItem no tiene provider."
            )

        quote_provider_code = (
            quote_attempt.provider_code or ""
        ).strip().upper()

        if quote_provider_code != provider_code:
            raise ValueError(
                "El provider del CotizacionItem no corresponde "
                "al provider de la cotización persistida."
            )

        successful_issue_exists = (
            CotizacionProveedorEmision.objects
            .filter(
                cotizacion_item=cotizacion_item,
                cotizacion_proveedor=quote_attempt,
                provider_code=provider_code,
                estatus=(
                    CotizacionProveedorEmision
                    .Estatus
                    .EXITOSA
                ),
            )
            .exists()
        )

        if successful_issue_exists:
            raise ValueError(
                "Ya existe una emisión exitosa para este "
                "CotizacionItem. No se permite emitir nuevamente."
            )

        successful_issue_exists = (
            CotizacionProveedorEmision.objects
            .filter(
                cotizacion_item=cotizacion_item,
                cotizacion_proveedor=quote_attempt,
                provider_code=provider_code,
                estatus=(
                    CotizacionProveedorEmision
                    .Estatus
                    .EXITOSA
                ),
            )
            .exists()
        )

        if successful_issue_exists:
            raise ValueError(
                "Ya existe una emisión exitosa para este "
                "CotizacionItem. No se permite emitir nuevamente."
            )
        
        unknown_issue_exists = (
            CotizacionProveedorEmision.objects
            .filter(
                cotizacion_item=cotizacion_item,
                cotizacion_proveedor=quote_attempt,
                provider_code=provider_code,
                estatus=(
                    CotizacionProveedorEmision
                    .Estatus
                    .INDETERMINADA
                ),
            )
            .exists()
        )

        if unknown_issue_exists:
            raise ValueError(
                "Existe una emisión con resultado indeterminado "
                "que requiere reconciliación antes de reintentar."
            )

        configuration = configuration_service.get_by_id(
            configuration_id,
        )

        if (
            configuration.provider.strip().upper()
            != provider_code
        ):
            raise ValueError(
                "La configuración persistida no corresponde "
                "al provider del CotizacionItem."
            )

        insured_exists = (
            CotizacionProveedorPersona.objects
            .filter(
                cotizacion=cotizacion_item.cotizacion,
                provider_code=provider_code,
                rol=(
                    CotizacionProveedorPersona
                    .Rol
                    .ASEGURADO
                ),
            )
            .exists()
        )

        if not insured_exists:
            person_resolver = person_resolver_factory()

            person_provider = person_resolver.build(
                provider_code=configuration.provider,
                ambiente=configuration.ambiente,
                ramo=configuration.ramo,
                configuration=configuration,
            )

            person_service.create_one(
                cotizacion=cotizacion_item.cotizacion,
                configuration=configuration,
                provider=person_provider,
            )

        resolver = resolver_factory(
            configuration_service=(
                configuration_service
            ),
        )

        provider = resolver.build(
            provider_code=configuration.provider,
            ambiente=configuration.ambiente,
            ramo=configuration.ramo,
            configuration=configuration,
        )

        request = request_service.build(
            cotizacion_item=cotizacion_item,
        )

        issue_service = issue_service_factory(
            providers=[provider],
        )

        attempt = issue_service.issue_one(
            configuration.provider,
            request,
        )

        attempt_persistence_service.save(
            cotizacion_item=cotizacion_item,
            cotizacion_proveedor=quote_attempt,
            provider_configuration_id=configuration_id,
            attempt=attempt,
        )

        if not attempt.success:
            message = (
                attempt.error.message
                if attempt.error is not None
                else "La emisión falló."
            )

            logger.error(
                "Falló emisión de póliza. "
                "cotizacion_id=%s cotizacion_item_id=%s "
                "provider=%s error_type=%s retryable=%s "
                "outcome_unknown=%s message=%s",
                cotizacion_item.cotizacion_id,
                cotizacion_item.id,
                provider_code,
                (
                    attempt.error.error_type
                    if attempt.error is not None
                    else None
                ),
                (
                    attempt.error.retryable
                    if attempt.error is not None
                    else None
                ),
                (
                    attempt.error.outcome_unknown
                    if attempt.error is not None
                    else None
                ),
                message,
            )

            raise ValueError(message)

        if attempt.result is None:
            raise ValueError(
                "La emisión terminó sin IssueResult."
            )

        return persistence_service.save(
            cotizacion_item=cotizacion_item,
            issue_result=attempt.result,
        )
