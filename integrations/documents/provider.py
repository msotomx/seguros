from __future__ import annotations

from typing import Protocol

from integrations.documents.contracts import (
    PolicyDocumentRequest,
    PolicyDocumentResult,
)


class DocumentProvider(Protocol):
    @property
    def provider_code(self) -> str:
        ...

    def get_policy_documents(
        self,
        request: PolicyDocumentRequest,
    ) -> PolicyDocumentResult:
        ...
