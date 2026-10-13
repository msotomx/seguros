from __future__ import annotations
import base64
import binascii
from typing import Any

from integrations.providers.chubb.document_contracts import (
    ChubbPolicyDocumentRequest,
)

from integrations.documents.contracts import (
    PolicyDocument,
    PolicyDocumentResult,
)


class ChubbPolicyDocumentRequestMapper:
    @staticmethod
    def to_payload(
        request: ChubbPolicyDocumentRequest,
    ) -> dict[str, Any]:
        if not isinstance(request, ChubbPolicyDocumentRequest):
            raise TypeError(
                "request debe ser ChubbPolicyDocumentRequest."
            )

        policy: dict[str, Any] = {
            "policyKey": request.policy_key,
            "policyId": request.policy_id,
            "generateAllReceipts": request.generate_all_receipts,
            "copies": request.copies,
        }

        if request.risk_number is not None:
            policy["riskNumber"] = request.risk_number

        return {
            "policies": [policy],
        }

class ChubbPolicyDocumentResponseMapper:
    PROVIDER_CODE = "CHUBB"

    @classmethod
    def to_internal(
        cls,
        *,
        response: dict[str, Any],
        request: ChubbPolicyDocumentRequest,
    ) -> PolicyDocumentResult:
        if not isinstance(response, dict):
            raise TypeError("response debe ser dict.")

        if not isinstance(request, ChubbPolicyDocumentRequest):
            raise TypeError(
                "request debe ser ChubbPolicyDocumentRequest."
            )

        raw_policies = response.get("policies")

        if not isinstance(raw_policies, list) or not raw_policies:
            raise ValueError(
                "Chubb respondió sin pólizas."
            )

        policy = cls._find_policy(
            policies=raw_policies,
            request=request,
        )

        if policy.get("success") is not True:
            raise ValueError(
                "Chubb no generó los documentos de la póliza."
            )

        raw_documents = policy.get("documents")

        if not isinstance(raw_documents, list) or not raw_documents:
            raise ValueError(
                "Chubb respondió sin documentos de póliza."
            )

        documents: list[PolicyDocument] = []

        for raw_document in raw_documents:
            if not isinstance(raw_document, dict):
                raise ValueError(
                    "Chubb devolvió un documento inválido."
                )

            file_name = str(
                raw_document.get("fileName") or ""
            ).strip()

            order_id = str(
                raw_document.get("orderId") or ""
            ).strip()

            encoded_document = raw_document.get("document")

            if not file_name:
                raise ValueError(
                    "Chubb devolvió un documento sin fileName."
                )

            if (
                not isinstance(encoded_document, str)
                or not encoded_document
            ):
                raise ValueError(
                    "Chubb devolvió un documento sin contenido."
                )

            try:
                content = base64.b64decode(
                    encoded_document,
                    validate=True,
                )
            except (binascii.Error, ValueError) as exc:
                raise ValueError(
                    "Chubb devolvió Base64 inválido "
                    f"para {file_name}."
                ) from exc

            if not content:
                raise ValueError(
                    "Chubb devolvió un documento vacío "
                    f"para {file_name}."
                )

            documents.append(
                PolicyDocument(
                    order_id=order_id,
                    file_name=file_name,
                    content=content,
                )
            )

        return PolicyDocumentResult(
            provider_code=cls.PROVIDER_CODE,
            provider_policy_id=str(request.policy_id),
            provider_policy_key=request.policy_key,
            documents=tuple(documents),
            raw_response=response,
        )

    @staticmethod
    def _find_policy(
        *,
        policies: list[Any],
        request: ChubbPolicyDocumentRequest,
    ) -> dict[str, Any]:
        for policy in policies:
            if not isinstance(policy, dict):
                continue

            policy_key = str(
                policy.get("policyKey") or ""
            ).strip()

            policy_id = str(
                policy.get("policyId") or ""
            ).strip()

            if (
                policy_key == request.policy_key
                and policy_id == str(request.policy_id)
            ):
                return policy

        raise ValueError(
            "Chubb no devolvió la póliza solicitada."
        )
