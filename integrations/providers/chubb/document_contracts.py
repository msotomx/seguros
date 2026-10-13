from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChubbPolicyDocumentRequest:
    policy_key: str
    policy_id: int
    risk_number: int | None
    generate_all_receipts: bool
    copies: int


@dataclass(frozen=True, slots=True)
class ChubbPolicyDocumentItem:
    order_id: str
    file_name: str
    document: str


@dataclass(frozen=True, slots=True)
class ChubbPolicyDocumentResult:
    success: bool
    documents: tuple[ChubbPolicyDocumentItem, ...]
