from __future__ import annotations

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.documents.contracts import (
    PolicyDocumentRequest,
    PolicyDocumentResult,
)
from integrations.documents.provider_resolver_factory import (
    build_document_provider_resolver,
)
from integrations.documents.service import DocumentService
from polizas.models import Poliza, PolizaProveedor
from documentos.models import Documento
from cotizador.services.policy_document_persistence_service import (
    PolicyDocumentPersistenceService,
)
from integrations.providers.exceptions import (
    ProviderHttpTimeoutError,
)


class PortalDocumentApplicationService:
    """
    Caso de uso para obtener los documentos de una póliza.

    Coordina:

    Poliza
        ↓
    PolizaProveedor
        ↓
    CotizacionItem / provider_option
        ↓
    ProviderConfiguration
        ↓
    DocumentProviderResolver
        ↓
    PolicyDocumentRequest
        ↓
    DocumentService
        ↓
    PolicyDocumentResult

    No persiste archivos.
    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    def get_policy_documents(
        cls,
        *,
        poliza: Poliza,
        configuration_service=ProviderConfigurationService,
        resolver_factory=build_document_provider_resolver,
        document_service_factory=DocumentService,
    ) -> PolicyDocumentResult:
        if not isinstance(poliza, Poliza):
            raise TypeError(
                "poliza debe ser una instancia de Poliza."
            )

        try:
            provider_result = poliza.resultado_proveedor
        except PolizaProveedor.DoesNotExist as exc:
            raise ValueError(
                "La póliza no tiene resultado de provider."
            ) from exc

        cotizacion_item = poliza.cotizacion_item

        if cotizacion_item is None:
            raise ValueError(
                "La póliza no tiene CotizacionItem."
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
            provider_result.provider_code or ""
        ).strip().upper()

        if not provider_code:
            raise ValueError(
                "La póliza no tiene provider_code."
            )

        item_provider_code = (
            cotizacion_item.provider or ""
        ).strip().upper()

        if item_provider_code != provider_code:
            raise ValueError(
                "El provider de la póliza no corresponde "
                "al provider del CotizacionItem."
            )

        quote_provider_code = (
            quote_attempt.provider_code or ""
        ).strip().upper()

        if quote_provider_code != provider_code:
            raise ValueError(
                "El provider de la póliza no corresponde "
                "al provider de la cotización persistida."
            )

        configuration = configuration_service.get_by_id(
            configuration_id,
        )

        configuration_provider_code = (
            configuration.provider or ""
        ).strip().upper()

        if configuration_provider_code != provider_code:
            raise ValueError(
                "La configuración persistida no corresponde "
                "al provider de la póliza."
            )

        provider_policy_id = (
            provider_result.provider_policy_id or ""
        ).strip()

        if not provider_policy_id:
            raise ValueError(
                "La póliza no tiene provider_policy_id."
            )

        provider_policy_key = (
            provider_result.provider_policy_key or ""
        ).strip()

        if not provider_policy_key:
            raise ValueError(
                "La póliza no tiene provider_policy_key."
            )

        risk_number = None

        if provider_option.riesgo is not None:
            risk_number = (
                provider_option.riesgo.risk_number
            )

        request = PolicyDocumentRequest(
            provider_policy_id=provider_policy_id,
            provider_policy_key=provider_policy_key,
            risk_number=risk_number,
        )

        resolver = resolver_factory(
            configuration_service=configuration_service,
        )

        provider = resolver.build(
            provider_code=configuration.provider,
            ambiente=configuration.ambiente,
            ramo=configuration.ramo,
            configuration=configuration,
        )

        document_service = document_service_factory(
            providers=[provider],
        )

        return document_service.get_policy_documents(
            configuration.provider,
            request,
        )

    @classmethod
    def get_and_persist_policy_document(
        cls,
        *,
        poliza: Poliza,
        subido_por=None,
        configuration_service=ProviderConfigurationService,
        resolver_factory=build_document_provider_resolver,
        document_service_factory=DocumentService,
        persistence_service=PolicyDocumentPersistenceService,
    ) -> Documento:
        if not isinstance(poliza, Poliza):
            raise TypeError(
                "poliza debe ser una instancia de Poliza."
            )

        if poliza.documento_id is not None:
            return poliza.documento

        try:
            result = cls.get_policy_documents(
                poliza=poliza,
                configuration_service=configuration_service,
                resolver_factory=resolver_factory,
                document_service_factory=document_service_factory,
            )
        except ProviderHttpTimeoutError:
            result = cls.get_policy_documents(
                poliza=poliza,
                configuration_service=configuration_service,
                resolver_factory=resolver_factory,
                document_service_factory=document_service_factory,
            )
    
        if not result.documents:
            raise ValueError(
                "El provider no devolvió documentos de póliza."
            )

        if len(result.documents) != 1:
            raise ValueError(
                "El provider devolvió más de un documento "
                "de póliza y no se puede determinar cuál persistir."
            )

        return persistence_service.persist(
            poliza=poliza,
            document=result.documents[0],
            subido_por=subido_por,
        )
