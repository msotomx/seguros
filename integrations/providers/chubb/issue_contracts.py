from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# ======================================================================
# Issue - Request contracts
# ======================================================================


@dataclass(frozen=True, slots=True)
class ChubbIssuePersonRequest:
    """
    Identidad de una persona previamente registrada en Chubb.
    """

    tran_id: int
    person_id: int
    address_id: int


@dataclass(frozen=True, slots=True)
class ChubbIssueItemDetailRequest:
    """
    Datos del riesgo que Chubb requiere para emitir.
    """

    number: int
    package_id: int
    no_serie: str
    plate: str
    engine_number: str
    reference: str

    owner_tran_id: int
    owner_id: int
    owner_address_id: int

    beneficiary_tran_id: int
    beneficiary_id: int


@dataclass(frozen=True, slots=True)
class ChubbIssueItemRequest:
    """
    Wrapper utilizado por Chubb para cada riesgo.
    """

    item: ChubbIssueItemDetailRequest


@dataclass(frozen=True, slots=True)
class ChubbIssueInvoiceRequest:
    """
    Información fiscal utilizada durante emisión.
    """

    legal_personality_id: int
    rfc: str
    name: str
    postal_code: str
    tax_regime: int
    use_cfdi_id: int
    email: str
    email_payment: str
    comments: str
    purchase_order: str


@dataclass(frozen=True, slots=True)
class ChubbIssueRequest:
    """
    Solicitud completa para POST /issue.
    """

    quote_id: int
    payment_type_id: int
    insured: ChubbIssuePersonRequest
    items: tuple[ChubbIssueItemRequest, ...]
    invoice: ChubbIssueInvoiceRequest | None = None

# ======================================================================
# Issue - Response contracts
# ======================================================================


@dataclass(frozen=True, slots=True)
class ChubbIssueItemResult:
    """
    Primas finales del riesgo emitido.
    """

    number: int
    net_premium_amount: float
    right_amount: float
    discount_amount: float
    surcharge_amount: float
    iva_amount: float
    total_premium_amount: float


@dataclass(frozen=True, slots=True)
class ChubbIssueResult:
    """
    Resultado de una emisión exitosa en Chubb.
    """

    quote_key: str
    quote_policy_id: int

    net_premium_amount: float
    bonification_amount: float
    surcharge_amount: float
    discount_amount: float
    total_premium_amount: float

    insured_id: int
    insured_address_id: int

    items: tuple[ChubbIssueItemResult, ...]

    raw_response: Mapping[str, Any]
