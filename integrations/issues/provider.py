from __future__ import annotations

from typing import Protocol, runtime_checkable

from integrations.issues.contracts import (
    InternalIssueRequest,
    IssueResult,
)


@runtime_checkable
class IssueProvider(Protocol):
    """
    Contrato común para cualquier proveedor de emisión.
    """

    provider_code: str

    def issue(
        self,
        request: InternalIssueRequest,
    ) -> IssueResult:
        """
        Emite una póliza y devuelve un resultado normalizado.
        """
        ...
