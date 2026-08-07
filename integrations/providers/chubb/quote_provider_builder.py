from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)

from integrations.providers.chubb.internal_quote_mapper import (
    ChubbInternalQuoteRequestMapper,
)
from integrations.providers.chubb.quote_client import ChubbQuoteClient
from integrations.providers.chubb.quote_provider import ChubbQuoteProvider


class ChubbQuoteProviderBuilder:
    """
    Construye un ChubbQuoteProvider listo para cotizar.

    Responsabilidades:
    - obtener ProviderConfiguration;
    - validar campos estructurales;
    - validar ProviderSetting obligatorios;
    - construir el mapper interno;
    - construir el cliente de cotización;
    - ensamblar el provider.

    No realiza llamadas HTTP.
    No construye requests de negocio.
    No contiene valores operativos hardcodeados.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        configuration_service=ProviderConfigurationService,
        client_factory=ChubbQuoteClient,
        mapper_factory=ChubbInternalQuoteRequestMapper,
        provider_factory=ChubbQuoteProvider,
    ) -> None:
        self._configuration_service = configuration_service
        self._client_factory = client_factory
        self._mapper_factory = mapper_factory
        self._provider_factory = provider_factory

    def build(
        self,
        *,
        ambiente: str,
        ramo: str,
    ) -> ChubbQuoteProvider:
        configuration = (
            self._configuration_service.get_active(
                provider=self.provider_code,
                ambiente=ambiente,
                ramo=ramo,
            )
        )

        if not configuration.supports_quote:
            raise InvalidProviderSetting(
                "La configuración activa de Chubb no tiene "
                "habilitada la operación de cotización."
            )

        request_mapper = self._mapper_factory(
            product_id=self._required_positive_setting(
                configuration,
                "PRODUCT_ID",
            ),
            business_profile_id=self._required_positive_field(
                configuration,
                "business_profile_id",
            ),
            agent_id=self._required_text_setting(
                configuration,
                "AGENT_OPTION_ID",
            ),
            conduit_id=self._required_non_negative_setting(
                configuration,
                "CONDUIT_ID",
            ),
            grouping_id=self._required_positive_field(
                configuration,
                "grouping_id",
            ),
            rate_id=self._required_positive_field(
                configuration,
                "rate_id",
            ),
            calculation_type_id=self._required_positive_setting(
                configuration,
                "CALCULATION_TYPE_ID",
            ),
            currency_id=self._required_positive_setting(
                configuration,
                "CURRENCY_ID",
            ),
            payment_type_id=self._required_positive_setting(
                configuration,
                "PAYMENT_TYPE_ID",
            ),
            insured_amount_type_id=(
                self._required_positive_setting(
                    configuration,
                    "INSURED_AMOUNT_TYPE_ID",
                )
            ),
            deductible_type_id=self._required_positive_setting(
                configuration,
                "DEDUCTIBLE_TYPE_ID",
            ),
            nadasc=self._required_bool_setting(
                configuration,
                "NADASC",
            ),
            gender_ids=self._required_gender_ids(
                configuration,
                "GENDER_IDS",
            ),
        )

        client = self._client_factory(
            ambiente=ambiente,
            ramo=ramo,
            configuration_service=(
                self._configuration_service
            ),
        )

        return self._provider_factory(
            client=client,
            request_mapper=request_mapper,
        )

    @staticmethod
    def _required_field(
        configuration,
        field_name: str,
    ) -> Any:
        value = getattr(
            configuration,
            field_name,
            None,
        )

        if value in (None, ""):
            raise InvalidProviderSetting(
                "La configuración de Chubb no contiene "
                f"el campo obligatorio '{field_name}'."
            )

        return value

    @classmethod
    def _required_positive_field(
        cls,
        configuration,
        field_name: str,
    ) -> int:
        value = cls._required_field(
            configuration,
            field_name,
        )

        return cls._positive_int(
            value,
            field_name,
        )

    @staticmethod
    def _required_setting(
        configuration,
        key: str,
    ) -> Any:
        try:
            return configuration.require_setting(key)
        except ValueError as exc:
            raise InvalidProviderSetting(
                f"Falta el ProviderSetting obligatorio '{key}'."
            ) from exc

    @classmethod
    def _required_positive_setting(
        cls,
        configuration,
        key: str,
    ) -> int:
        value = cls._required_setting(
            configuration,
            key,
        )

        return cls._positive_int(
            value,
            key,
        )

    @classmethod
    def _required_non_negative_setting(
        cls,
        configuration,
        key: str,
    ) -> int:
        value = cls._required_setting(
            configuration,
            key,
        )

        normalized = cls._integer(
            value,
            key,
        )

        if normalized < 0:
            raise InvalidProviderSetting(
                f"'{key}' debe ser cero o mayor."
            )

        return normalized

    @classmethod
    def _required_text_setting(
        cls,
        configuration,
        key: str,
    ) -> str:
        value = cls._required_setting(
            configuration,
            key,
        )

        normalized = str(value).strip()

        if not normalized:
            raise InvalidProviderSetting(
                f"'{key}' no puede estar vacío."
            )

        return normalized

    @classmethod
    def _required_bool_setting(
        cls,
        configuration,
        key: str,
    ) -> bool:
        value = cls._required_setting(
            configuration,
            key,
        )

        if not isinstance(value, bool):
            raise InvalidProviderSetting(
                f"'{key}' debe ser booleano."
            )

        return value

    @classmethod
    def _required_gender_ids(
        cls,
        configuration,
        key: str,
    ) -> dict[str, int]:
        value = cls._required_setting(
            configuration,
            key,
        )

        if not isinstance(value, Mapping):
            raise InvalidProviderSetting(
                f"'{key}' debe ser un objeto JSON."
            )

        result: dict[str, int] = {}

        for internal_code, external_id in value.items():
            normalized_code = str(
                internal_code
            ).strip().upper()

            if not normalized_code:
                raise InvalidProviderSetting(
                    f"'{key}' contiene un código vacío."
                )

            result[normalized_code] = cls._positive_int(
                external_id,
                f"{key}.{normalized_code}",
            )

        if not result:
            raise InvalidProviderSetting(
                f"'{key}' no puede estar vacío."
            )

        return result

    @classmethod
    def _positive_int(
        cls,
        value: Any,
        field_name: str,
    ) -> int:
        normalized = cls._integer(
            value,
            field_name,
        )

        if normalized <= 0:
            raise InvalidProviderSetting(
                f"'{field_name}' debe ser mayor que cero."
            )

        return normalized

    @staticmethod
    def _integer(
        value: Any,
        field_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise InvalidProviderSetting(
                f"'{field_name}' debe ser entero."
            )

        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidProviderSetting(
                f"'{field_name}' debe ser entero."
            ) from exc
