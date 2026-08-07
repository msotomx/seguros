import json
from decimal import Decimal
from typing import Any

from integrations.broker.provider_configuration import ProviderConfiguration
from integrations.configuration.exceptions import (
    InvalidProviderSetting,
    ProviderConfigurationNotFound,
)
from integrations.models import (
    AseguradoraConfiguracion,
    ProviderSetting,
)


class ProviderConfigurationService:
    """
    Obtiene y normaliza la configuración de Insurance Providers.

    Responsabilidades:
    - Consultar AseguradoraConfiguracion.
    - Leer los ProviderSetting activos.
    - Convertir cada valor a su tipo correspondiente.
    - Entregar un ProviderConfiguration independiente del ORM.

    No inicializa Providers.
    No realiza llamadas HTTP.
    No contiene lógica de cotización.
    """

    @classmethod
    def get_active(
        cls,
        provider: str,
        ambiente: str = AseguradoraConfiguracion.Ambiente.SIT,
        ramo: str = AseguradoraConfiguracion.Ramo.AUTOS,
    ) -> ProviderConfiguration:
        config_model = (
            AseguradoraConfiguracion.objects
            .select_related("aseguradora")
            .prefetch_related("settings")
            .filter(
                provider=provider,
                ambiente=ambiente,
                ramo=ramo,
                activo=True,
            )
            .order_by("prioridad", "id")
            .first()
        )

        if not config_model:
            raise ProviderConfigurationNotFound(
                "No existe configuración activa para "
                f"provider={provider}, ambiente={ambiente}, ramo={ramo}."
            )

        settings = cls._build_settings(config_model)

        return ProviderConfiguration(
            id=config_model.id,
            provider=config_model.provider,
            ambiente=config_model.ambiente,
            ramo=config_model.ramo,
            nombre=config_model.nombre,
            aseguradora_id=config_model.aseguradora_id,
            activo=config_model.activo,
            prioridad=config_model.prioridad,
            token_url=config_model.token_url,
            base_url=config_model.base_url,
            client_id=config_model.client_id,
            client_secret=config_model.client_secret,
            resource_id=config_model.resource_id,
            api_version=config_model.api_version,
            timeout=config_model.timeout,
            grouping_id=config_model.grouping_id,
            rate_id=config_model.rate_id,
            business_profile_id=config_model.business_profile_id,
            business_profile_name=config_model.business_profile_name,
            source_application_id=config_model.source_application_id,
            supports_quote=config_model.supports_quote,
            supports_issue=config_model.supports_issue,
            supports_documents=config_model.supports_documents,
            supports_payments=config_model.supports_payments,
            supports_endorsements=config_model.supports_endorsements,
            supports_cancellation=config_model.supports_cancellation,
            supports_renewal=config_model.supports_renewal,
            settings=settings,
        )

    @classmethod
    def _build_settings(
        cls,
        config_model: AseguradoraConfiguracion,
    ) -> dict[str, Any]:
        result = {}

        for setting in config_model.settings.all():
            if not setting.activo:
                continue

            result[setting.key] = cls._convert_setting_value(setting)

        return result

    @staticmethod
    def _convert_setting_value(setting: ProviderSetting) -> Any:
        value = setting.value
        value_type = setting.value_type

        try:
            if value_type == ProviderSetting.ValueType.STRING:
                return value

            if value_type == ProviderSetting.ValueType.INTEGER:
                return int(value)

            if value_type == ProviderSetting.ValueType.DECIMAL:
                return Decimal(value)

            if value_type == ProviderSetting.ValueType.BOOLEAN:
                normalized = value.strip().lower()

                if normalized in {"true", "1", "yes", "si", "sí"}:
                    return True

                if normalized in {"false", "0", "no"}:
                    return False

                raise ValueError(
                    "El booleano debe ser true/false, 1/0, yes/no o sí/no."
                )

            if value_type == ProviderSetting.ValueType.JSON:
                return json.loads(value)

        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InvalidProviderSetting(
                f"Valor inválido para el parámetro "
                f"'{setting.key}' ({value_type}): {value!r}"
            ) from exc

        raise InvalidProviderSetting(
            f"Tipo no soportado para '{setting.key}': {value_type}"
        )
