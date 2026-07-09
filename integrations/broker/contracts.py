from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from typing import Any


@dataclass
class BrokerVehicleData:
    tipo_uso: str | None = None
    anio: int | None = None
    marca: str | None = None
    submarca: str | None = None
    version: str | None = None
    placas: str | None = None
    vin: str | None = None
    codigo_postal: str | None = None


@dataclass
class BrokerCustomerData:
    tipo_cliente: str
    nombre: str
    email: str | None = None
    telefono: str | None = None
    codigo_postal: str | None = None
    ciudad: str | None = None
    estado: str | None = None
    nombre_comercial: str | None = None


@dataclass
class BrokerQuoteRequest:
    cotizacion_id: int | None
    cliente: BrokerCustomerData
    vehiculo: BrokerVehicleData
    vigencia_desde: date | None = None
    vigencia_hasta: date | None = None
    forma_pago: str | None = None
    notas: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Deductible:
    coverage: str
    value: str | None = None


@dataclass
class Coverage:
    name: str
    insured_amount: Decimal | None = None
    deductible: str | None = None


@dataclass
class BrokerQuoteOption:
    provider: str
    provider_quote_id: str | None
    product_name: str
    package_name: str | None
    currency: str = "MXN"

    prima_total: Decimal = Decimal("0.00")
    prima_neta: Decimal | None = None
    derechos: Decimal | None = None
    iva: Decimal | None = None
    recargos: Decimal | None = None

    payment_type: str | None = None
    valid_until: date | None = None

    coverages: list[Coverage] = field(default_factory=list)
    deductibles: list[Deductible] = field(default_factory=list)

    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerQuoteResult:
    request: BrokerQuoteRequest
    options: list[BrokerQuoteOption] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.options)


@dataclass
class BrokerIssueRequest:
    provider: str
    provider_quote_id: str
    cotizacion_item_id: int | None = None
    cliente_id: int | None = None
    vehiculo_id: int | None = None
    payment_type: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerIssuedPolicy:
    provider: str
    policy_number: str
    provider_policy_id: str | None = None
    issued_at: datetime | None = None
    vigencia_desde: date | None = None
    vigencia_hasta: date | None = None
    prima_total: Decimal | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerPolicyDocument:
    provider: str
    policy_number: str
    document_type: str
    filename: str
    content_type: str | None = None
    content_base64: str | None = None
    download_url: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerPaymentLink:
    provider: str
    provider_quote_id: str | None = None
    provider_policy_id: str | None = None
    url: str | None = None
    expires_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
