from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class PolicyDocumentRequest:
    provider_policy_id: str
    provider_policy_key: str
    risk_number: int | None = None


@dataclass(frozen=True, slots=True)
class PolicyDocument:
    order_id: str
    file_name: str
    content: bytes


@dataclass(frozen=True, slots=True)
class PolicyDocumentResult:
    provider_code: str
    provider_policy_id: str
    provider_policy_key: str
    documents: tuple[PolicyDocument, ...]
    raw_response: Mapping[str, Any] | None = None
