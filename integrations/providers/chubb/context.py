from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from integrations.catalog import CatalogService
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.contracts import (
    ChubbQuoteContext,
)
from integrations.providers.contracts import (
    QuoteRequest,
)
from integrations.providers.exceptions import (
    ProviderQuoteContextError,
)


class ChubbQuoteContextResolver:
    """
    Construye ChubbQuoteContext a partir de:

    - ProviderConfigurationService
    - CatalogService
    - QuoteRequest

    No construye el payload.
    No realiza HTTP.
    No autentica.
    """

    def __init__(
        self,
        *,
        provider_id: int,
        provider: str,
        ambiente: str,
        ramo: str,
        configuration_service: Any = ProviderConfigurationService,
        catalog_service: Any = CatalogService,
    ):
        if not isinstance(provider_id, int) or provider_id <= 0:
            raise ValueError(
                "provider_id debe ser un entero mayor que cero."
            )

        self.provider_id = provider_id
        self.provider = provider
        self.ambiente = ambiente
        self.ramo = ramo
        self.configuration_service = configuration_service
        self.catalog_service = catalog_service

    def resolve(
        self,
        *,
        request: QuoteRequest,
    ) -> ChubbQuoteContext:
        self._validate_request(request)

        configuration = self.configuration_service.get_active(
            provider=self.provider,
            ambiente=self.ambiente,
            ramo=self.ramo,
        )

        if configuration.id != self.provider_id:
            raise ProviderQuoteContextError(
                "La configuración activa obtenida no corresponde "
                "al provider_id del adapter."
            )

        settings = configuration.settings or {}

        vehicle_mapping = self._resolve_mapping(
            catalog_code="VEHICLE",
            internal_code=request.vehicle.version_code,
        )

        vehicle_use_mapping = self._resolve_mapping(
            catalog_code="VEHICLE_USE",
            internal_code=request.vehicle.use_code,
        )

        payment_mapping = self._resolve_mapping(
            catalog_code="PAYMENT_FREQUENCY",
            internal_code=request.payment_frequency_code,
        )

        package_mapping = self._resolve_mapping(
            catalog_code="COVERAGE_PACKAGE",
            internal_code=request.coverage_code,
        )

        state_code = self._metadata_code(
            request,
            key="state_code",
        )
        municipality_code = self._metadata_code(
            request,
            key="municipality_code",
        )

        state_mapping = self._resolve_mapping(
            catalog_code="STATE",
            internal_code=state_code,
        )

        municipality_mapping = self._resolve_mapping(
            catalog_code="MUNICIPALITY",
            internal_code=municipality_code,
        )

        vehicle_id = self._mapping_metadata_int(
            vehicle_mapping,
            key="vehicle_id",
        )

        return ChubbQuoteContext(
            product_id=self._required_setting_int(
                settings,
                "PRODUCT_ID",
            ),
            business_profile_id=self._required_setting_int(
                settings,
                "BUSINESS_PROFILE_ID",
            ),
            agent_id=self._required_setting_int(
                settings,
                "AGENT_ID",
            ),
            conduit_id=self._required_setting_int(
                settings,
                "CONDUIT_ID",
                allow_zero=True,
            ),
            grouping_id=self._required_setting_int(
                settings,
                "GROUPING_ID",
            ),
            rate_id=self._required_setting_int(
                settings,
                "RATE_ID",
            ),
            calculation_type_id=self._required_setting_int(
                settings,
                "CALCULATION_TYPE_ID",
            ),
            currency_id=self._required_setting_int(
                settings,
                "CURRENCY_ID",
            ),
            payment_type_id=self._external_int(
                payment_mapping,
            ),
            vehicle_key=self._external_text(
                vehicle_mapping,
            ),
            vehicle_id=vehicle_id,
            insured_amount_type_id=self._required_setting_int(
                settings,
                "INSURED_AMOUNT_TYPE_ID",
            ),
            deductible_type_id=self._required_setting_int(
                settings,
                "DEDUCTIBLE_TYPE_ID",
            ),
            country_subdivision_id=self._external_int(
                state_mapping,
            ),
            municipality_id=self._external_int(
                municipality_mapping,
            ),
            vehicle_use_id=self._external_int(
                vehicle_use_mapping,
            ),
            package_id=self._external_int(
                package_mapping,
            ),
            source_application=self._optional_setting_int(
                settings,
                "SOURCE_APPLICATION",
                default=23,
            ),
            discount_percentage=self._optional_setting_decimal(
                settings,
                "DISCOUNT_PERCENTAGE",
                default=Decimal("0"),
            ),
            bonus_percentage=self._optional_setting_decimal(
                settings,
                "BONUS_PERCENTAGE",
                default=Decimal("0"),
            ),
            garage_use=self._optional_setting_bool(
                settings,
                "GARAGE_USE",
                default=False,
            ),
            nadasc=self._optional_setting_bool(
                settings,
                "NADASC",
                default=False,
            ),
            reference=str(
                settings.get("QUOTE_REFERENCE", "SWITCHH")
            ).strip() or "SWITCHH",
            prospect_name=self._prospect_name(
                request=request,
                settings=settings,
            ),
            metadata={
                "configuration_id": configuration.id,
                "provider": configuration.provider,
                "ambiente": configuration.ambiente,
                "ramo": configuration.ramo,
            },
        )

    def _resolve_mapping(
        self,
        *,
        catalog_code: str,
        internal_code: str,
    ):
        try:
            return self.catalog_service.to_provider(
                provider_id=self.provider_id,
                catalog_code=catalog_code,
                internal_code=internal_code,
            )
        except Exception as exc:
            raise ProviderQuoteContextError(
                "No fue posible resolver el catálogo "
                f"'{catalog_code}' con valor '{internal_code}'."
            ) from exc

    @staticmethod
    def _validate_request(
        request: QuoteRequest,
    ) -> None:
        if not isinstance(request, QuoteRequest):
            raise TypeError(
                "request debe ser una instancia de QuoteRequest."
            )

    def _metadata_code(
        self,
        request: QuoteRequest,
        *,
        key: str,
    ) -> str:
        value = request.metadata.get(key)

        if value is None or not str(value).strip():
            raise ProviderQuoteContextError(
                f"QuoteRequest.metadata no contiene '{key}'."
            )

        return str(value).strip().upper()

    @staticmethod
    def _required_setting_int(
        settings: dict,
        key: str,
        *,
        allow_zero: bool = False,
    ) -> int:
        if key not in settings:
            raise ProviderQuoteContextError(
                f"Falta el ProviderSetting '{key}'."
            )

        try:
            value = int(settings[key])
        except (TypeError, ValueError) as exc:
            raise ProviderQuoteContextError(
                f"El ProviderSetting '{key}' debe ser entero."
            ) from exc

        minimum = 0 if allow_zero else 1

        if value < minimum:
            raise ProviderQuoteContextError(
                f"El ProviderSetting '{key}' debe ser "
                f"{'cero o mayor' if allow_zero else 'mayor que cero'}."
            )

        return value

    @classmethod
    def _optional_setting_int(
        cls,
        settings: dict,
        key: str,
        *,
        default: int,
    ) -> int:
        if key not in settings:
            return default

        return cls._required_setting_int(
            settings,
            key,
            allow_zero=False,
        )

    @staticmethod
    def _optional_setting_decimal(
        settings: dict,
        key: str,
        *,
        default: Decimal,
    ) -> Decimal:
        if key not in settings:
            return default

        try:
            return Decimal(str(settings[key]))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ProviderQuoteContextError(
                f"El ProviderSetting '{key}' debe ser decimal."
            ) from exc

    @staticmethod
    def _optional_setting_bool(
        settings: dict,
        key: str,
        *,
        default: bool,
    ) -> bool:
        if key not in settings:
            return default

        value = settings[key]

        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()

        if normalized in {"true", "1", "yes", "si", "sí"}:
            return True

        if normalized in {"false", "0", "no"}:
            return False

        raise ProviderQuoteContextError(
            f"El ProviderSetting '{key}' debe ser booleano."
        )

    @staticmethod
    def _external_int(mapping) -> int:
        try:
            value = int(mapping.external_code)
        except (TypeError, ValueError) as exc:
            raise ProviderQuoteContextError(
                f"El código externo de "
                f"'{mapping.catalog_code}:{mapping.internal_code}' "
                "debe ser entero."
            ) from exc

        if value <= 0:
            raise ProviderQuoteContextError(
                f"El código externo de "
                f"'{mapping.catalog_code}:{mapping.internal_code}' "
                "debe ser mayor que cero."
            )

        return value

    @staticmethod
    def _external_text(mapping) -> str:
        value = str(mapping.external_code).strip()

        if not value:
            raise ProviderQuoteContextError(
                f"El código externo de "
                f"'{mapping.catalog_code}:{mapping.internal_code}' "
                "está vacío."
            )

        return value

    @staticmethod
    def _mapping_metadata_int(
        mapping,
        *,
        key: str,
    ) -> int:
        value = mapping.metadata.get(key)

        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderQuoteContextError(
                f"El mapeo '{mapping.catalog_code}:"
                f"{mapping.internal_code}' no contiene "
                f"metadata válida para '{key}'."
            ) from exc

        if normalized <= 0:
            raise ProviderQuoteContextError(
                f"El metadata '{key}' debe ser mayor que cero."
            )

        return normalized

    @staticmethod
    def _prospect_name(
        *,
        request: QuoteRequest,
        settings: dict,
    ) -> str:
        configured = str(
            settings.get("PROSPECT_NAME", "")
        ).strip()

        if configured:
            return configured

        full_name = " ".join(
            part.strip()
            for part in [
                request.insured.first_name,
                request.insured.last_name,
                request.insured.second_last_name,
            ]
            if part and part.strip()
        )

        return full_name or "SWITCHH"
    