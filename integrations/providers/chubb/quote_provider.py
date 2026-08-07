from __future__ import annotations

from integrations.quotes.adapters.quote_adapter import (
    ChubbQuoteAdapter,
)
from integrations.quotes.contracts import (
    InternalQuoteRequest,
    QuoteResult,
)

from integrations.providers.chubb.internal_quote_mapper import (
    ChubbInternalQuoteRequestMapper,
)
from integrations.providers.chubb.quote_client import ChubbQuoteClient


class ChubbQuoteProvider:
    """
    Adaptador entre QuoteService y la integración específica de Chubb.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        client: ChubbQuoteClient,
        request_mapper: ChubbInternalQuoteRequestMapper,
    ) -> None:
        self._client = client
        self._request_mapper = request_mapper

    def quote(
        self,
        request: InternalQuoteRequest,
    ) -> QuoteResult:
        chubb_request = self._request_mapper.create_quote(
            request
        )

        chubb_result = self._client.create_quote(
            chubb_request
        )

        return ChubbQuoteAdapter.to_quote_result(
            chubb_result
        )
