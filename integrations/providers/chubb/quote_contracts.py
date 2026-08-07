from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping
from decimal import Decimal

# ======================================================================
# Create Quote - Request contracts
# ======================================================================


@dataclass(frozen=True, slots=True)
class ChubbQuotePaymentTypeRequest:
    """
    Forma de pago solicitada para la cotización.
    """

    payment_type_id: int


@dataclass(frozen=True, slots=True)
class ChubbQuoteDiscountRequest:
    """
    Descuento o bonificación aplicada a un riesgo.
    """

    discount_type_id: int
    discount_tag: str
    discount_percentage: float = 0.0


@dataclass(frozen=True, slots=True)
class ChubbQuoteDriverRequest:
    """
    Identificadores del conductor dentro de Chubb.

    Para una cotización nueva, Chubb acepta estos valores en cero.
    """

    tran_id: int = 0
    person_id: int = 0
    address_id: int = 0


@dataclass(frozen=True, slots=True)
class ChubbQuoteVehicleRequest:
    """
    Información del vehículo y del conductor utilizada para tarifar.
    """
    vehicle_key: str
    insured_amount_type_id: int
    deductible_type_id: int
    year: int
    country_subdivision_id: int
    municipality_id: int
    use_id: int
    garage_use: bool
    nadasc: bool
    reference: str
    plate: str
    age: int
    gender_id: int
    driver: ChubbQuoteDriverRequest


@dataclass(frozen=True, slots=True)
class ChubbQuoteCoverageRequest:
    """
    Cobertura que se desea incluir o personalizar dentro del paquete.
    """

    coverage_id: int
    insurance_amount: float
    deductible_type_id: int
    deductible_value: float
    coverage_custom_description: str = ""


@dataclass(frozen=True, slots=True)
class ChubbQuotePackageRequest:
    """
    Paquete solicitado para un riesgo.
    """

    package_id: int
    selected: bool
    coverages: tuple[ChubbQuoteCoverageRequest, ...] = ()


@dataclass(frozen=True, slots=True)
class ChubbQuoteItemRequest:
    """
    Riesgo incluido en la cotización.

    En una cotización nueva, risk_id normalmente se envía en cero.
    """

    risk_id: int
    risk_number: int
    vehicle: ChubbQuoteVehicleRequest
    packages: tuple[ChubbQuotePackageRequest, ...]
    discounts: tuple[ChubbQuoteDiscountRequest, ...] = ()


@dataclass(frozen=True, slots=True)
class ChubbCreateQuoteRequest:
    """
    Solicitud completa para POST /digital.quote.partners/quote.
    """

    product_id: int
    business_profile_id: int
    agent_id: str
    conduit_id: int
    grouping_id: int
    rate_id: int
    effective_date: date
    expiration_date: date
    calculation_type_id: int
    currency_id: int
    reference: str
    prospect_name: str
    payment_types: tuple[ChubbQuotePaymentTypeRequest, ...]
    items: tuple[ChubbQuoteItemRequest, ...]


# ======================================================================
# Create Quote - Response contracts
# ======================================================================


@dataclass(frozen=True, slots=True)
class ChubbQuoteDiscountResult:
    """
    Descuento calculado por Chubb.
    """

    discount_type_id: int
    discount_tag: str
    discount_percentage: float
    discount_amount: float


@dataclass(frozen=True, slots=True)
class ChubbQuoteCoverageResult:
    """
    Cobertura devuelta por Chubb.

    Muchos campos de la respuesta pueden venir en null, por lo que
    se modelan como opcionales.
    """

    coverage_id: int
    description: str
    custom_name: str | None
    insured_amount: float | None
    premium: float
    deductible_type_id: int | None
    deductible_value: float | None
    selected: bool


@dataclass(frozen=True, slots=True)
class ChubbQuotePackageResult:
    """
    Paquete cotizado.
    """
    package_id: int
    description: str | None
    total_premium: float
    selected: bool
    coverages: tuple[ChubbQuoteCoverageResult, ...]


@dataclass(frozen=True, slots=True)
class ChubbQuoteItemResult:
    """
    Riesgo cotizado.

    Estos identificadores normalmente se utilizan posteriormente
    para emisión, endosos y renovaciones.
    """

    risk_id: int
    risk_number: int
    vehicle_key: str
    packages: tuple[ChubbQuotePackageResult, ...]


@dataclass(frozen=True, slots=True)
class ChubbCreateQuoteResult:
    """
    Resultado principal de Create Quote.
    La primera implementación modela los identificadores y totales
    necesarios para continuar el flujo, conservando además la respuesta
    completa de Chubb en raw_response.

    Los campos de comisión e impuesto porcentual pueden venir como null.

    """

    quote_id: int
    quote_version_id: int

    base_net_premium: float
    base_net_premium_without_discount: float

    discounts: tuple[ChubbQuoteDiscountResult, ...]

    surcharge_percentage: float | None
    surcharge_amount: float

    fee_amount: float

    tax_percentage: float | None
    tax_amount: float

    total_premium_amount: float

    commission_percentage: float | None
    commission_amount: float | None
    surcharge_commission_amount: float | None

    items: tuple[ChubbQuoteItemResult, ...]

    raw_response: Mapping[str, Any]

@dataclass(frozen=True, slots=True)
class ChubbZoneDiscount:
    country_subdivision_id: int
    country_subdivision_name: str
    percentage_discount: Decimal | None = None
