from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


# Contrato del Token

@dataclass(frozen=True, slots=True)
class ChubbAccessToken:
    access_token: str
    token_type: str
    expires_in: int
    ext_expires_in: int | None = None
    expires_on: int | None = None
    not_before: int | None = None
    resource: str = ""

    @property
    def authorization_header(self) -> str:
        return f"{self.token_type} {self.access_token}"
    

@dataclass(frozen=True, slots=True)
class ChubbHttpResponse:
    status_code: int
    data: Any
    headers: Mapping[str, str]

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass(frozen=True, slots=True)
class ChubbQuoteContext:
    """
    Valores específicos de Chubb necesarios para construir /quote.

    Estos valores ya deben venir resueltos mediante:
    - ProviderConfigurationService
    - CatalogService
    - Catálogos externos de Chubb
    """

    product_id: int
    business_profile_id: int
    agent_id: int
    conduit_id: int
    grouping_id: int
    rate_id: int
    calculation_type_id: int
    currency_id: int
    payment_type_id: int

    vehicle_key: str
    vehicle_id: int
    insured_amount_type_id: int
    deductible_type_id: int

    country_subdivision_id: int
    municipality_id: int
    vehicle_use_id: int
    package_id: int

    source_application: int = 23

    discount_percentage: Decimal = Decimal("0")
    bonus_percentage: Decimal = Decimal("0")

    garage_use: bool = False
    nadasc: bool = False

    reference: str = "SWITCHH"
    prospect_name: str = "SWITCHH"

    metadata: Mapping[str, Any] | None = None

@dataclass(frozen=True, slots=True)
class ChubbBusinessProfile:
    business_profile_id: int
    name: str
    description: str

@dataclass(frozen=True, slots=True)
class ChubbAgent:
    agent_option_id: int
    name: str
    description: str = ""
    

@dataclass(frozen=True, slots=True)
class ChubbCalculationType:
    calculation_type_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbConduit:
    conduit_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbCurrency:
    currency_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbGrouping:
    grouping_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbRate:
    rate_id: int
    name: str
    description: str
    rate_type_id: int

@dataclass(frozen=True, slots=True)
class ChubbPaymentType:
    payment_type_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbInsuredAmountType:
    insured_amount_type_id: int
    name: str
    description: str
    is_default: bool | None
    vehicle_class_id: int
    vehicle_condition_id: int

@dataclass(frozen=True, slots=True)
class ChubbPackage:
    package_id: int
    name: str
    description: str = ""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChubbVehicleMake:
    make_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbVehicleSubmake:
    submake_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbVehicleType:
    vehicle_type_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbVehicleYear:
    year: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbVehicleData:
    vehicle_id: int
    description: str
    vehicle_type_id: int
    trailer_id: int
    tonnage_id: int
    short_description: str
    long_description: str
    tonnage: float
    passengers: int
    cmst: str
    cmst_consecutive: int
    active: bool
    status: int
    make_id: int
    submake_id: int
    vehicle_type_description: str
    trailer_type_description: str
    submake_description: str
    make_description: str
    tonnage_description: str
    class_id: int
    vehicle_group_id: int
    vehicle_group_description: str
    status_description: str
    mtc: str
    vehicle_key: str
    vehicle_condition_id: int

@dataclass(frozen=True, slots=True)
class ChubbCountrySubdivision:
    subdivision_id: int
    name: str
    description: str = ""

@dataclass(frozen=True, slots=True)
class ChubbVehicleUse:
    service_id: int
    service_description: str
    use_id: int
    use_description: str
