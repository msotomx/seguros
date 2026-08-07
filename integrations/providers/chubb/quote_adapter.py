from __future__ import annotations

from typing import Any

from integrations.providers.chubb.auth import (
    ChubbAuthClient,
)
from integrations.providers.chubb.context import (
    ChubbQuoteContextResolver,
)
from integrations.providers.chubb.http_client import (
    ChubbHttpClient,
)
from integrations.providers.chubb.payloads import (
    ChubbQuotePayloadBuilder,
)
from integrations.providers.chubb.responses import (
    ChubbQuoteResponseMapper,
)
from integrations.providers.contracts import (
    QuoteRequest,
    QuoteResponse,
)
from integrations.providers.exceptions import (
    ProviderError,
    ProviderQuoteError,
)
from integrations.providers.insurance_base import (
    BaseInsuranceProviderAdapter,
)


class ChubbQuoteAdapter(BaseInsuranceProviderAdapter):
    """
    Adapter de operaciones salientes para Chubb.

    Coordina:
    - autenticación;
    - Valida que el QuoteRequest corresponda al provider.
    - resolución del contexto técnico;
    - construcción del payload;
    - comunicación HTTP;
    - normalización de la respuesta.
    - Traduce valores canónicos mediante CatalogService.


    No contiene reglas de catálogo ni detalles del JSON.
    """

    provider_code = "CHUBB"

    supported_operations = frozenset({
        "quote",
    })

    quote_path = "/quote"

    def __init__(
        self,
        *,
        provider_id: int,
        ambiente: str,
        ramo: str,
        configuration_service=None,
        catalog_service=None,
        auth_client=None,
        context_resolver=None,
        http_client=None,
        payload_builder=None,
        response_mapper=None,
    ):
        base_kwargs = {}

        if configuration_service is not None:
            base_kwargs["configuration_service"] = (
                configuration_service
            )

        if catalog_service is not None:
            base_kwargs["catalog_service"] = catalog_service

        super().__init__(**base_kwargs)

        if not isinstance(provider_id, int) or provider_id <= 0:
            raise ValueError(
                "provider_id debe ser un entero mayor que cero."
            )

        if not isinstance(ambiente, str) or not ambiente.strip():
            raise ValueError(
                "ambiente no puede estar vacío."
            )

        if not isinstance(ramo, str) or not ramo.strip():
            raise ValueError(
                "ramo no puede estar vacío."
            )

        self.provider_id = provider_id
        self.ambiente = ambiente
        self.ramo = ramo

        self.auth_client = auth_client or ChubbAuthClient(
            provider=self.provider_code,
            ambiente=self.ambiente,
            ramo=self.ramo,
            configuration_service=self.configuration_service,
        )

        self.context_resolver = (
            context_resolver
            or ChubbQuoteContextResolver(
                provider_id=self.provider_id,
                provider=self.provider_code,
                ambiente=self.ambiente,
                ramo=self.ramo,
                configuration_service=(
                    self.configuration_service
                ),
                catalog_service=self.catalog_service,
            )
        )

        self.http_client = (
            http_client
            or self._build_http_client()
        )

        self.payload_builder = (
            payload_builder
            or ChubbQuotePayloadBuilder
        )

        self.response_mapper = (
            response_mapper
            or ChubbQuoteResponseMapper
        )

    def authenticate(self):
        return self.auth_client.get_token()

    def quote(
        self,
        *,
        request: QuoteRequest,
    ) -> QuoteResponse:
        self.ensure_supported("quote")
        self._validate_request(request)

        try:
            token = self.authenticate()

            context = self.context_resolver.resolve(
                request=request,
            )

            payload = self.payload_builder.build(
                request=request,
                context=context,
            )

            quote_headers = (
                self.payload_builder.build_headers(
                    context=context,
                )
            )

            http_response = self.http_client.post(
                self.quote_path,
                token=token,
                payload=payload,
                headers=quote_headers,
            )

            return self.response_mapper.map(
                provider_id=self.provider_id,
                payload=http_response.data,
            )

        except ProviderError:
            # Conservamos las excepciones normalizadas del engine.
            raise

        except Exception as exc:
            raise ProviderQuoteError(
                "Ocurrió un error inesperado al ejecutar "
                "la cotización con Chubb."
            ) from exc

    def _build_http_client(
        self,
    ) -> ChubbHttpClient:
        configuration = (
            self.configuration_service.get_active(
                provider=self.provider_code,
                ambiente=self.ambiente,
                ramo=self.ramo,
            )
        )

        if configuration.id != self.provider_id:
            raise ProviderQuoteError(
                "La configuración activa no corresponde "
                "al provider_id del ChubbAdapter."
            )

        return ChubbHttpClient(
            base_url=configuration.base_url,
            api_version=str(configuration.api_version),
            timeout=configuration.timeout,
        )

    def _validate_request(
        self,
        request: QuoteRequest,
    ) -> None:
        if not isinstance(request, QuoteRequest):
            raise TypeError(
                "request debe ser una instancia de QuoteRequest."
            )

        if request.provider_id != self.provider_id:
            raise ProviderQuoteError(
                "El provider_id del QuoteRequest no corresponde "
                "al provider configurado en ChubbAdapter."
            )
                