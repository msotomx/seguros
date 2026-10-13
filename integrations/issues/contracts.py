from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class IssueMessage:
    level: str
    message: str
    code: str | None = None


@dataclass(frozen=True, slots=True)
class IssuePartyReference:
    """
    Identidad de una persona previamente registrada
    ante el proveedor.
    """

    provider_tran_id: str
    provider_person_id: str
    provider_address_id: str | None = None


@dataclass(frozen=True, slots=True)
class IssueRisk:
    """
    Riesgo seleccionado para emisión.
    """

    risk_number: int
    provider_package_id: str
    vin: str
    reference: str
    plate: str | None = None
    engine_number: str | None = None
    owner: IssuePartyReference | None = None
    beneficiary: IssuePartyReference | None = None


@dataclass(frozen=True, slots=True)
class IssueInvoice:
    """
    Datos fiscales normalizados.

    Los códigos son internos del ERP.
    El provider será responsable de convertirlos
    a sus identificadores externos.
    """

    tax_id: str
    name: str
    postal_code: str
    legal_personality_code: str
    tax_regime_code: str
    cfdi_use_code: str
    email: str
    payment_email: str | None = None
    comments: str = ""
    purchase_order: str = ""


@dataclass(frozen=True, slots=True)
class InternalIssueRequest:
    """
    Solicitud de emisión independiente del proveedor.
    """

    provider_quote_id: str
    provider_quote_version_id: str | None
    payment_method_code: str
    insured: IssuePartyReference
    risks: tuple[IssueRisk, ...]
    invoice: IssueInvoice | None = None


@dataclass(frozen=True, slots=True)
class IssueRiskResult:
    risk_number: int
    net_premium: Decimal
    fees: Decimal
    surcharge: Decimal
    discount: Decimal
    taxes: Decimal
    total_premium: Decimal


@dataclass(frozen=True, slots=True)
class IssueResult:
    """
    Resultado normalizado de una emisión.

    Los nombres específicos del proveedor permanecen
    únicamente en raw_response.
    """

    provider_code: str

    provider_policy_id: str

    provider_policy_key: str | None

    policy_number: str | None

    currency: str

    net_premium: Decimal

    fees: Decimal

    surcharge: Decimal

    discount: Decimal

    taxes: Decimal

    total_premium: Decimal

    risks: tuple[IssueRiskResult, ...] = ()

    messages: tuple[IssueMessage, ...] = ()

    raw_response: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class IssueProviderError:
    provider_code: str
    message: str
    error_type: str
    retryable: bool = False
    outcome_unknown: bool = False


@dataclass(frozen=True, slots=True)
class IssueAttempt:
    provider_code: str
    success: bool
    elapsed_ms: int

    result: IssueResult | None = None
    error: IssueProviderError | None = None

    def __post_init__(self) -> None:
        if self.success:
            if self.result is None:
                raise ValueError(
                    "Un IssueAttempt exitoso requiere result."
                )

            if self.error is not None:
                raise ValueError(
                    "Un IssueAttempt exitoso no puede contener error."
                )

        else:
            if self.error is None:
                raise ValueError(
                    "Un IssueAttempt fallido requiere error."
                )

            if self.result is not None:
                raise ValueError(
                    "Un IssueAttempt fallido no puede contener result."
                )
