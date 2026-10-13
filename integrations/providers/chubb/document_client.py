from __future__ import annotations

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.documents.contracts import (
    PolicyDocumentResult,
)
from integrations.providers.chubb.auth import ChubbAuthClient
from integrations.providers.chubb.document_contracts import (
    ChubbPolicyDocumentRequest,
)
from integrations.providers.chubb.document_mappers import (
    ChubbPolicyDocumentRequestMapper,
    ChubbPolicyDocumentResponseMapper,
)
from integrations.providers.chubb.http_client import ChubbHttpClient
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


class ChubbDocumentClient:
    """
    Cliente de Policy Documents Chubb.

    No construye contratos internos de solicitud.
    No resuelve catálogos.
    No contiene URLs operativas hardcodeadas.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        ambiente: str,
        ramo: str,
        configuration_service=ProviderConfigurationService,
        configuration=None,
        auth_client=None,
        http_client=None,
    ):
        self.ambiente = ambiente.strip()
        self.ramo = ramo.strip()
        self.configuration_service = configuration_service

        if configuration is None:
            configuration = (
                self.configuration_service.get_active(
                    provider=self.provider_code,
                    ambiente=self.ambiente,
                    ramo=self.ramo,
                )
            )

        self.configuration = configuration

        self.auth_client = auth_client or ChubbAuthClient(
            provider=self.provider_code,
            ambiente=self.ambiente,
            ramo=self.ramo,
            configuration_service=self.configuration_service,
            configuration=self.configuration,
        )

        if http_client is not None:
            self.http_client = http_client
        else:
            self.http_client = ChubbHttpClient(
                base_url=self._documents_base_url(
                    self.configuration
                ),
                api_version=str(
                    self.configuration.api_version
                ),
                timeout=self.configuration.timeout,
            )

    def get_policy_documents(
        self,
        request: ChubbPolicyDocumentRequest,
    ) -> PolicyDocumentResult:
        if not isinstance(
            request,
            ChubbPolicyDocumentRequest,
        ):
            raise ProviderInvalidResponseError(
                "request debe ser ChubbPolicyDocumentRequest."
            )

        try:
            payload = (
                ChubbPolicyDocumentRequestMapper.to_payload(
                    request
                )
            )
        except (TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc

        source_application_id = (
            self.configuration.source_application_id
        )

        if source_application_id is None:
            raise ProviderInvalidResponseError(
                "Chubb no tiene configurado "
                "'source_application_id'."
            )

        token = self.auth_client.get_token()

        response = self.http_client.post(
            "/documents/policy",
            token=token,
            payload=payload,
            headers={
                "CB-SourceApplication": str(
                    source_application_id
                ),
            },
        )

        try:
            return ChubbPolicyDocumentResponseMapper.to_internal(
                response=response.data,
                request=request,
            )
        except (TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc

    @staticmethod
    def _documents_base_url(
        configuration,
    ) -> str:
        try:
            value = configuration.require_setting(
                "DOCUMENTS_BASE_URL"
            )
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                "Falta el ProviderSetting obligatorio "
                "'DOCUMENTS_BASE_URL'."
            ) from exc

        normalized = str(value).strip()

        if not normalized:
            raise ProviderInvalidResponseError(
                "'DOCUMENTS_BASE_URL' no puede estar vacío."
            )

        return normalized
