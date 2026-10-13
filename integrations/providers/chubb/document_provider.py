from __future__ import annotations

from integrations.documents.contracts import (
    PolicyDocumentRequest,
    PolicyDocumentResult,
)
from integrations.providers.chubb.document_client import (
    ChubbDocumentClient,
)
from integrations.providers.chubb.internal_document_mapper import (
    ChubbInternalDocumentRequestMapper,
)


class ChubbDocumentProvider:
    """
    Adaptador entre DocumentService y Policy Documents de Chubb.

    No obtiene ProviderConfiguration.
    No construye clientes.
    No contiene valores operativos hardcodeados.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        client: ChubbDocumentClient,
        request_mapper: ChubbInternalDocumentRequestMapper,
    ) -> None:
        self._client = client
        self._request_mapper = request_mapper

    def get_policy_documents(
        self,
        request: PolicyDocumentRequest,
    ) -> PolicyDocumentResult:
        chubb_request = self._request_mapper.map(request)

        return self._client.get_policy_documents(
            chubb_request
        )
