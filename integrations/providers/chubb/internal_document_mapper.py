from __future__ import annotations

from integrations.documents.contracts import PolicyDocumentRequest
from integrations.providers.chubb.document_contracts import (
    ChubbPolicyDocumentRequest,
)


class ChubbInternalDocumentRequestMapper:
    def __init__(
        self,
        *,
        generate_all_receipts: bool,
        copies: int,
    ) -> None:
        if not isinstance(generate_all_receipts, bool):
            raise TypeError(
                "generate_all_receipts debe ser bool."
            )

        if not isinstance(copies, int) or isinstance(copies, bool):
            raise TypeError(
                "copies debe ser int."
            )

        if copies < 0:
            raise ValueError(
                "copies no puede ser negativo."
            )

        self._generate_all_receipts = generate_all_receipts
        self._copies = copies

    def map(
        self,
        request: PolicyDocumentRequest,
    ) -> ChubbPolicyDocumentRequest:
        if not isinstance(request, PolicyDocumentRequest):
            raise TypeError(
                "request debe ser PolicyDocumentRequest."
            )

        policy_id = request.provider_policy_id.strip()
        policy_key = request.provider_policy_key.strip()

        if not policy_id:
            raise ValueError(
                "provider_policy_id es requerido."
            )

        if not policy_key:
            raise ValueError(
                "provider_policy_key es requerido."
            )

        try:
            numeric_policy_id = int(policy_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "provider_policy_id debe ser numérico para Chubb."
            ) from exc

        return ChubbPolicyDocumentRequest(
            policy_key=policy_key,
            policy_id=numeric_policy_id,
            risk_number=request.risk_number,
            generate_all_receipts=self._generate_all_receipts,
            copies=self._copies,
        )
