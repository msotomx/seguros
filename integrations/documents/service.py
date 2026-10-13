from __future__ import annotations

from integrations.documents.contracts import (
    PolicyDocumentRequest,
    PolicyDocumentResult,
)
from integrations.documents.provider import DocumentProvider


class DocumentService:
    def __init__(
        self,
        providers: list[DocumentProvider],
    ) -> None:
        self._providers: dict[str, DocumentProvider] = {}

        for provider in providers:
            provider_code = provider.provider_code.strip().upper()

            if not provider_code:
                raise ValueError(
                    "DocumentProvider.provider_code no puede estar vacío."
                )

            if provider_code in self._providers:
                raise ValueError(
                    f"DocumentProvider duplicado: {provider_code}."
                )

            self._providers[provider_code] = provider

    def get_policy_documents(
        self,
        provider_code: str,
        request: PolicyDocumentRequest,
    ) -> PolicyDocumentResult:
        normalized_code = provider_code.strip().upper()

        provider = self._providers.get(normalized_code)

        if provider is None:
            raise ValueError(
                f"No existe DocumentProvider para {normalized_code}."
            )

        return provider.get_policy_documents(request)
