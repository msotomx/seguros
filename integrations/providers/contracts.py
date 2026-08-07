from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class QuoteVehicle:
    year: int
    brand_code: str
    model_code: str
    version_code: str
    use_code: str
    postal_code: str
    serial_number: str = ""
    engine_number: str = ""
    plates: str = ""


@dataclass(frozen=True, slots=True)
class QuoteInsured:
    person_type: str
    first_name: str
    last_name: str
    second_last_name: str = ""
    birth_date: date | None = None
    gender_code: str = ""
    marital_status_code: str = ""
    email: str = ""
    phone: str = ""
    tax_id: str = ""


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    provider_id: int
    vehicle: QuoteVehicle
    insured: QuoteInsured
    start_date: date
    end_date: date
    payment_frequency_code: str
    coverage_code: str
    currency: str = "MXN"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QuoteAmount:
    net_premium: Decimal
    taxes: Decimal
    fees: Decimal
    total: Decimal
    currency: str = "MXN"


@dataclass(frozen=True, slots=True)
class QuoteResponse:
    provider_id: int
    provider_quote_id: str
    status: str
    amount: QuoteAmount
    raw_response: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


class InsuranceProviderAdapter(Protocol):
    """
    Contrato común para adapters de aseguradoras.
    """

    provider_code: str

    def authenticate(self) -> None:
        ...

    def quote(
        self,
        *,
        request: QuoteRequest,
    ) -> QuoteResponse:
        ...

    def supports(
        self,
        operation: str,
    ) -> bool:
        ...
