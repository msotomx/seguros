from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.internal_person_mapper import (
    ChubbInternalPersonRequestMapper,
)
from integrations.providers.chubb.person_client import (
    ChubbPersonClient,
)
from integrations.providers.chubb.person_provider import (
    ChubbPersonProvider,
)


class ChubbPersonProviderBuilder:
    """
    Construye un ChubbPersonProvider listo para Create Person.

    Responsabilidades:
    - obtener ProviderConfiguration;
    - validar configuración requerida;
    - construir el mapper interno;
    - construir el cliente;
    - ensamblar el provider.

    No realiza llamadas HTTP.
    No construye PersonRequest.
    No contiene valores operativos hardcodeados.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        configuration_service=ProviderConfigurationService,
        client_factory=ChubbPersonClient,
        mapper_factory=ChubbInternalPersonRequestMapper,
        provider_factory=ChubbPersonProvider,
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
    ) -> ChubbPersonProvider:
        configuration = (
            self._configuration_service.get_active(
                provider=self.provider_code,
                ambiente=ambiente,
                ramo=ramo,
            )
        )

        if not configuration.supports_issue:
            raise InvalidProviderSetting(
                "La configuración activa de Chubb no tiene "
                "habilitada la operación de emisión."
            )

        provider_id = self._positive_int(
            configuration.id,
            "id",
        )

        # El cliente utiliza este setting como base URL.
        # Lo validamos aquí para fallar antes de construir
        # un provider incompleto.
        self._required_text_setting(
            configuration,
            "PERSON_BASE_URL",
        )

        request_mapper = self._mapper_factory(
            person_type_id=(
                self._nullable_non_negative_setting(
                    configuration,
                    "PERSON_TYPE_ID",
                )
            ),
            legal_personality_id=(
                self._required_non_negative_setting(
                    configuration,
                    "LEGAL_PERSONALITY_ID",
                )
            ),
            marital_status_id=(
                self._required_positive_setting(
                    configuration,
                    "MARITAL_STATUS_ID",
                )
            ),
            address_type_id=(
                self._required_positive_setting(
                    configuration,
                    "ADDRESS_TYPE_ID",
                )
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
            provider_id=provider_id,
            client=client,
            request_mapper=request_mapper,
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
    def _nullable_non_negative_setting(
        cls,
        configuration,
        key: str,
    ) -> int | None:
        if key not in configuration.settings:
            raise InvalidProviderSetting(
                f"Falta el ProviderSetting obligatorio '{key}'."
            )

        value = configuration.settings[key]

        if value is None:
            return None

        normalized = cls._integer(
            value,
            key,
        )

        if normalized < 0:
            raise InvalidProviderSetting(
                f"'{key}' debe ser null, cero o mayor."
            )

        return normalized

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
