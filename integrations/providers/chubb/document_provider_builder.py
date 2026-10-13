from __future__ import annotations

from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.document_client import (
    ChubbDocumentClient,
)
from integrations.providers.chubb.document_provider import (
    ChubbDocumentProvider,
)
from integrations.providers.chubb.internal_document_mapper import (
    ChubbInternalDocumentRequestMapper,
)


class ChubbDocumentProviderBuilder:
    """
    Construye un ChubbDocumentProvider listo para Policy Documents.

    No realiza llamadas HTTP.
    No construye PolicyDocumentRequest.
    No contiene valores operativos hardcodeados.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        configuration_service=ProviderConfigurationService,
        client_factory=ChubbDocumentClient,
        mapper_factory=ChubbInternalDocumentRequestMapper,
        provider_factory=ChubbDocumentProvider,
    ) -> None:
        self._configuration_service = configuration_service
        self._client_factory = client_factory
        self._mapper_factory = mapper_factory
        self._provider_factory = provider_factory

    def build(
        self,
        *,
        ambiente: str,
        ramo: str,
        configuration=None,
    ) -> ChubbDocumentProvider:
        if configuration is None:
            configuration = (
                self._configuration_service.get_active(
                    provider=self.provider_code,
                    ambiente=ambiente,
                    ramo=ramo,
                )
            )

        if not configuration.supports_documents:
            raise InvalidProviderSetting(
                "La configuración activa de Chubb no tiene "
                "habilitada la operación de documentos."
            )

        self._required_text_setting(
            configuration,
            "DOCUMENTS_BASE_URL",
        )

        generate_all_receipts = self._required_boolean_setting(
            configuration,
            "DOCUMENTS_GENERATE_ALL_RECEIPTS",
        )

        copies = self._required_non_negative_integer_setting(
            configuration,
            "DOCUMENTS_COPIES",
        )

        request_mapper = self._mapper_factory(
            generate_all_receipts=generate_all_receipts,
            copies=copies,
        )

        client = self._client_factory(
            ambiente=ambiente,
            ramo=ramo,
            configuration_service=self._configuration_service,
            configuration=configuration,
        )

        return self._provider_factory(
            client=client,
            request_mapper=request_mapper,
        )

    @staticmethod
    def _required_setting(
        configuration,
        key: str,
    ):
        try:
            return configuration.require_setting(key)
        except ValueError as exc:
            raise InvalidProviderSetting(
                f"Falta el ProviderSetting obligatorio '{key}'."
            ) from exc

    @classmethod
    def _required_text_setting(
        cls,
        configuration,
        key: str,
    ) -> str:
        value = cls._required_setting(configuration, key)
        normalized = str(value).strip()

        if not normalized:
            raise InvalidProviderSetting(
                f"'{key}' no puede estar vacío."
            )

        return normalized

    @classmethod
    def _required_boolean_setting(
        cls,
        configuration,
        key: str,
    ) -> bool:
        value = cls._required_setting(configuration, key)

        if not isinstance(value, bool):
            raise InvalidProviderSetting(
                f"'{key}' debe ser booleano."
            )

        return value

    @classmethod
    def _required_non_negative_integer_setting(
        cls,
        configuration,
        key: str,
    ) -> int:
        value = cls._required_setting(configuration, key)

        if isinstance(value, bool):
            raise InvalidProviderSetting(
                f"'{key}' debe ser entero."
            )

        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidProviderSetting(
                f"'{key}' debe ser entero."
            ) from exc

        if normalized < 0:
            raise InvalidProviderSetting(
                f"'{key}' debe ser cero o mayor."
            )

        return normalized
