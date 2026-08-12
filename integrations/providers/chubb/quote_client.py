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
from integrations.providers.chubb.quote_contracts import (
    ChubbCreateQuoteRequest,
    ChubbCreateQuoteResult,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)

from .quote_mappers import (
    ChubbQuoteRequestMapper,
    ChubbQuoteResponseMapper,
)


class ChubbQuoteClient:
    """
    Cliente de cotizaciones Chubb.

    Encargado únicamente de:

    - validar parámetros de entrada;
    - serializar el request;
    - ejecutar POST;
    - transformar la respuesta.
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

    def _post_quote(
        self,
        endpoint: str,
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
            endpoint,
            token=token,
            payload=payload,
            headers={
                "CB-SourceApplication": str(
                    source_application_id
                ),
            },
        )

        return response.data

    def get_quote(
        self,
        quote_id: int,
    ) -> ChubbCreateQuoteResult:
        if (
            not isinstance(quote_id, int)
            or isinstance(quote_id, bool)
            or quote_id <= 0
        ):
            raise ValueError(
                "quote_id debe ser un entero mayor que cero."
            )

        token = self.auth_client.get_token()

        response = self.http_client.get(
            "/quote",
            token=token,
            params={
                "quoteId": quote_id,
            },
        )

        try:
            return ChubbQuoteResponseMapper.get_quote(
                response.data
            )
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc

    def create_quote(
        self,
        request: ChubbCreateQuoteRequest,
    ) -> ChubbCreateQuoteResult:
        if not isinstance(
            request,
            ChubbCreateQuoteRequest,
        ):
            raise ProviderInvalidResponseError(
                "request debe ser "
                "ChubbCreateQuoteRequest."
            )

        try:
            payload = ChubbQuoteRequestMapper.create_quote(
                request,
            )
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc

        response_data = self._post_quote(
            "/quote",
            payload,
        )

        try:
            return ChubbQuoteResponseMapper.create_quote(
                response_data,
            )
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                str(exc)
            ) from exc
