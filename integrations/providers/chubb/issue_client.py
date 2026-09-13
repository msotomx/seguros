from __future__ import annotations

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.auth import (
    ChubbAuthClient,
)
from integrations.providers.chubb.http_client import (
    ChubbHttpClient,
)
from integrations.providers.chubb.issue_contracts import (
    ChubbIssueRequest,
    ChubbIssueResult,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)

from .issue_mappers import (
    ChubbIssueRequestMapper,
    ChubbIssueResponseMapper,
)


class ChubbIssueClient:
    """
    Cliente de emisión Chubb.

    Encargado únicamente de:

    - obtener configuración activa;
    - obtener token;
    - serializar el request;
    - ejecutar POST /issue;
    - transformar la respuesta.

    No conoce contratos internos del ERP.
    No conoce modelos Django.
    No persiste la póliza.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        ambiente: str,
        ramo: str,
        configuration_service=ProviderConfigurationService,
        auth_client=None,
        http_client=None,
    ):
        self.ambiente = ambiente.strip()
        self.ramo = ramo.strip()
        self.configuration_service = configuration_service

        self.configuration = (
            self.configuration_service.get_active(
                provider=self.provider_code,
                ambiente=self.ambiente,
                ramo=self.ramo,
            )
        )

        self.auth_client = auth_client or ChubbAuthClient(
            provider=self.provider_code,
            ambiente=self.ambiente,
            ramo=self.ramo,
            configuration_service=self.configuration_service,
        )

        self.http_client = http_client or ChubbHttpClient(
            base_url=self.configuration.base_url,
            api_version=str(
                self.configuration.api_version
            ),
            timeout=self.configuration.timeout,
        )

    def _post_issue(
        self,
        payload: dict,
    ):
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
            "/issue",
            token=token,
            payload=payload,
            headers={
                "CB-SourceApplication": str(
                    source_application_id
                ),
            },
        )

        return response.data

    def issue(
        self,
        request: ChubbIssueRequest,
    ) -> ChubbIssueResult:
        if not isinstance(
            request,
            ChubbIssueRequest,
        ):
            raise ProviderInvalidResponseError(
                "request debe ser "
                "ChubbIssueRequest."
            )

        try:
            payload = ChubbIssueRequestMapper.issue(
                request
            )
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc

        response_data = self._post_issue(
            payload
        )

        try:
            return ChubbIssueResponseMapper.issue(
                response_data
            )
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc
