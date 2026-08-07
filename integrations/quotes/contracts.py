from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping
from datetime import date


@dataclass(frozen=True, slots=True)
class QuoteMessage:
    """
    Mensaje normalizado producido por un proveedor.
    """

    level: str
    message: str
    code: str | None = None


@dataclass(frozen=True, slots=True)
class QuoteCoverage:
    """
    Cobertura normalizada.
    """

    code: str
    name: str

    insured_amount: Decimal | None = None

    deductible: Decimal | None = None

    premium: Decimal | None = None


@dataclass(frozen=True, slots=True)
class QuoteOption:
    """
    Opción o paquete de cotización.
    """

    code: str

    provider_package_id: int | None = None

    name: str = ""

    total_premium: Decimal = Decimal("0.00")

    currency: str = "MXN"

    selected: bool = False

    coverages: tuple[QuoteCoverage, ...] = ()


@dataclass(frozen=True, slots=True)
class QuoteRiskResult:
    reference: str | None = None

    provider_risk_id: str | None = None
    risk_number: int | None = None
    vehicle_key: str | None = None

    options: tuple[QuoteOption, ...] = ()


@dataclass(frozen=True, slots=True)
class QuoteResult:
    """
    Resultado normalizado de una aseguradora.

    Toda la información específica del proveedor permanece
    en raw_response.
    """

    provider_code: str

    provider_quote_id: str | None

    reference: str | None

    currency: str

    #
    # Importes
    #

    net_premium: Decimal

    fees: Decimal

    taxes: Decimal

    total_premium: Decimal

    #
    # Identificadores del proveedor
    #

    provider_quote_version_id: str | None = None

    #
    # Información comercial
    #

    options: tuple[QuoteOption, ...] = ()

    #
    # Riesgos normalizados
    #

    risks: tuple[QuoteRiskResult, ...] = ()

    messages: tuple[QuoteMessage, ...] = ()

    #
    # Respuesta completa del proveedor
    #

    raw_response: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class QuoteProviderError:
    """
    Error normalizado de un proveedor.

    No se expone directamente la excepción original a las capas
    superiores, pero se conserva su tipo para diagnóstico.
    """

    provider_code: str
    message: str
    error_type: str
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class QuoteAttempt:
    """
    Resultado de ejecutar un proveedor, exitoso o fallido.
    """

    provider_code: str
    success: bool
    elapsed_ms: int
    result: QuoteResult | None = None
    error: QuoteProviderError | None = None

    def __post_init__(self) -> None:
        if self.success:
            if self.result is None:
                raise ValueError(
                    "Un QuoteAttempt exitoso requiere result."
                )

            if self.error is not None:
                raise ValueError(
                    "Un QuoteAttempt exitoso no puede contener error."
                )

        else:
            if self.error is None:
                raise ValueError(
                    "Un QuoteAttempt fallido requiere error."
                )

            if self.result is not None:
                raise ValueError(
                    "Un QuoteAttempt fallido no puede contener result."
                )


@dataclass(frozen=True, slots=True)
class QuoteBatchResult:
    """
    Resultado consolidado de una ejecución multiaseguradora.
    """

    attempts: tuple[QuoteAttempt, ...] = field(
        default_factory=tuple
    )

    @property
    def successful(self) -> tuple[QuoteAttempt, ...]:
        return tuple(
            attempt
            for attempt in self.attempts
            if attempt.success
        )

    @property
    def failed(self) -> tuple[QuoteAttempt, ...]:
        return tuple(
            attempt
            for attempt in self.attempts
            if not attempt.success
        )

    @property
    def has_results(self) -> bool:
        return bool(self.successful)

    @property
    def best_price(self) -> QuoteResult | None:
        results = [
            attempt.result
            for attempt in self.successful
            if attempt.result is not None
        ]

        if not results:
            return None

        return min(
            results,
            key=lambda result: result.total_premium,
        )


# ==========================================================
# Datos del conductor
# ==========================================================

@dataclass(frozen=True, slots=True)
class QuoteDriver:

    age: int

    gender: str


# ==========================================================
# Vehículo
# ==========================================================

@dataclass(frozen=True, slots=True)
class QuoteVehicle:

    year: int

    vehicle_key: str

    use_code: str

    garage: bool

    state_code: str

    municipality_code: str

    plate: str | None = None


# ==========================================================
# Cobertura solicitada
# ==========================================================

@dataclass(frozen=True, slots=True)
class QuoteCoverageRequest:

    code: str

    insured_amount: Decimal | None = None

    deductible: Decimal | None = None


# ==========================================================
# Paquete solicitado
# ==========================================================

@dataclass(frozen=True, slots=True)
class QuotePackageRequest:

    code: str

    selected: bool = True

    coverages: tuple[
        QuoteCoverageRequest,
        ...
    ] = ()


# ==========================================================
# Descuento solicitado
# ==========================================================

@dataclass(frozen=True, slots=True)
class QuoteDiscountRequest:

    code: str

    percentage: Decimal = Decimal("0.00")


# ==========================================================
# Riesgo
# ==========================================================

@dataclass(frozen=True, slots=True)
class QuoteRisk:

    reference: str

    vehicle: QuoteVehicle

    driver: QuoteDriver

    packages: tuple[
        QuotePackageRequest,
        ...
    ]

    discounts: tuple[
        QuoteDiscountRequest,
        ...
    ] = ()


# ==========================================================
# Solicitud principal
# ==========================================================

@dataclass(frozen=True, slots=True)
class InternalQuoteRequest:

    effective_date: date

    expiration_date: date

    prospect_name: str

    reference: str

    risks: tuple[
        QuoteRisk,
        ...
    ]

