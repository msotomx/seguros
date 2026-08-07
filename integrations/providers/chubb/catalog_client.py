from __future__ import annotations

from typing import Any

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.auth import (
    ChubbAuthClient,
)
from integrations.providers.chubb.http_client import (
    ChubbHttpClient,
)
from integrations.providers.chubb.contracts import (
    ChubbAgent,
    ChubbBusinessProfile,
    ChubbCalculationType,
    ChubbConduit,
    ChubbCurrency,
    ChubbGrouping,
    ChubbRate,
    ChubbPaymentType,
    ChubbInsuredAmountType,
    ChubbPackage,
    ChubbVehicleMake,
    ChubbVehicleSubmake,
    ChubbVehicleType,
    ChubbVehicleYear,
    ChubbVehicleData,
    ChubbVehicleUse,
)
from integrations.providers.exceptions import (
    ProviderConfigurationError,
    ProviderInvalidResponseError,
)
from integrations.providers.chubb.catalog_mappers import ChubbCatalogMapper


class ChubbCatalogClient:
    """
    Cliente de catálogos de Chubb.

    Responsabilidades:
    - Obtener los parámetros propios de los catálogos.
    - Autenticarse mediante ChubbAuthClient.
    - Consultar los endpoints mediante ChubbHttpClient.
    - Convertir respuestas de Chubb a contratos inmutables.

    No guarda catálogos en la base de datos.
    No construye cotizaciones.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        ambiente: str,
        ramo: str,
        configuration_service: Any = ProviderConfigurationService,
        auth_client=None,
        http_client=None,
    ):
        self.ambiente = self._normalize_text(
            ambiente,
            field_name="ambiente",
        )
        self.ramo = self._normalize_text(
            ramo,
            field_name="ramo",
        )
        self.configuration_service = configuration_service

        self.configuration = (
            self.configuration_service.get_active(
                provider=self.provider_code,
                ambiente=self.ambiente,
                ramo=self.ramo,
            )
        )

        self.auth_client = auth_client or ChubbAuthClient(
            provider=self.provider_code,
            ambiente=self.ambiente,
            ramo=self.ramo,
            configuration_service=self.configuration_service,
        )

        self.http_client = http_client or ChubbHttpClient(
            base_url=self.configuration.base_url,
            api_version=str(
                self.configuration.api_version
            ),
            timeout=self.configuration.timeout,
        )

    def _get_catalog(
        self,
        endpoint: str,
        *,
        params: dict[str, Any],
    ):
        token = self.auth_client.get_token()

        response = self.http_client.get(
            endpoint,
            token=token,
            params=params,
        )

        return response.data

    def _required_business_profile_name(
        self,
        value: str,
    ) -> str:
        """
        Valida y normaliza el Business Profile Name
        utilizado por los catálogos de Chubb.
        """
        return self._normalize_text(
            value,
            field_name="business_profile_name",
        )

    def _required_setting_text(
        self,
        key: str,
    ) -> str:
        settings = self.configuration.settings or {}
        value = settings.get(key)

        if value is None or not str(value).strip():
            raise ProviderConfigurationError(
                f"Falta el ProviderSetting '{key}' "
                "en la configuración de Chubb."
            )

        return str(value).strip()

    @staticmethod
    def _normalize_text(
        value: Any,
        *,
        field_name: str,
    ) -> str:
        if value is None:
            raise ProviderInvalidResponseError(
                f"Falta el campo '{field_name}'."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ProviderInvalidResponseError(
                f"El campo '{field_name}' no puede estar vacío."
            )

        return normalized

    @staticmethod
    def _required_positive_int(
        value: Any,
        *,
        field_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise ProviderInvalidResponseError(
                f"El campo '{field_name}' debe ser entero."
            )

        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                f"El campo '{field_name}' debe ser entero."
            ) from exc

        if normalized <= 0:
            raise ProviderInvalidResponseError(
                f"El campo '{field_name}' debe ser "
                "mayor que cero."
            )

        return normalized

    @staticmethod
    def _required_text(
        value: Any,
        *,
        field_name: str,
    ) -> str:
        if value is None:
            raise ProviderInvalidResponseError(
                f"Falta el campo '{field_name}'."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ProviderInvalidResponseError(
                f"El campo '{field_name}' no puede estar vacío."
            )

        return normalized

    def business_profiles(
        self,
    ) -> tuple[ChubbBusinessProfile, ...]:
        """
        Consulta GET /catalogs/business-profiles.

        Requiere el ProviderSetting SYSTEM_NAME.
        """

        system_name = self._required_setting_text(
            "SYSTEM_NAME"
        )

        payload = self._get_catalog(
            "/catalogs/business-profiles",
            params={
                "SystemName": system_name,
            },
        )

        return ChubbCatalogMapper.map_business_profiles(
            payload
        )

    def agents(
        self,
        *,
        business_profile_name: str,
    ) -> tuple[ChubbAgent, ...]:
        """
        Consulta los agentes disponibles para un Business Profile.

        Endpoint:
            GET /catalogs/agents

        Query string:
            BusinessProfileName=<nombre>
        """

        business_profile_name = (
            self._required_business_profile_name(
                business_profile_name
            )
        )

        payload = self._get_catalog(
            "/catalogs/agents",
            params={
                "BusinessProfileName": business_profile_name,
            },
        )

        return ChubbCatalogMapper.map_agents(payload)

    def calculation_types(
        self,
        *,
        business_profile_name: str,
        agent_option_id: int,
    ) -> tuple[ChubbCalculationType, ...]:
        """
        Consulta los tipos de cálculo disponibles para un
        Business Profile.

        Endpoint:
            GET /catalogs/calculation-types

        Query string:
            BusinessProfileName=<nombre>
        """

        normalized_business_profile_name = (
            self._required_business_profile_name(
                business_profile_name
            )
        )

        normalized_agent_option_id = int(
            agent_option_id
        )

        if normalized_agent_option_id <= 0:
            raise ProviderInvalidResponseError(
                "agent_option_id debe ser un entero positivo."
            )

        params = {
            "BusinessProfileName": normalized_business_profile_name,
            "AgentOptionId": normalized_agent_option_id,
        }

        payload = self._get_catalog(
            "/catalogs/calculation-types",
            params=params,
        )


        return ChubbCatalogMapper.map_calculation_types(
            payload
        )
    
    def conduits(
        self,
        *,
        business_profile_name: str,
        agent_option_id: int,
    ) -> tuple[ChubbConduit, ...]:
        """
        Consulta los conductos disponibles para un
        Business Profile y un agente.

        Endpoint:
            GET /catalogs/conduits

        Query string:
            BusinessProfileName=<nombre>
            AgentOptionId=<id>
        """

        normalized_business_profile_name = (
            self._required_business_profile_name(
                business_profile_name
            )
        )

        normalized_agent_option_id = int(
            agent_option_id
        )

        if normalized_agent_option_id <= 0:
            raise ProviderInvalidResponseError(
                "agent_option_id debe ser un entero positivo."
            )

        params = {
            "BusinessProfileName": normalized_business_profile_name,
            "AgentOptionId": normalized_agent_option_id,
        }

        payload = self._get_catalog(
            "/catalogs/conduits",
            params=params,
        )

        return ChubbCatalogMapper.map_conduits(
            payload
        )

    def currencies(
        self,
        *,
        business_profile_name: str,
    ) -> tuple[ChubbCurrency, ...]:
        """
        Consulta las monedas disponibles para un
        Business Profile.

        Endpoint:
            GET /catalogs/currencies

        Query string:
            BusinessProfileName=<nombre>
        """

        normalized_business_profile_name = (
            self._required_business_profile_name(
                business_profile_name
            )
        )

        params = {
            "BusinessProfileName": normalized_business_profile_name,
        }

        payload = self._get_catalog(
            "/catalogs/currencies",
            params=params,
        )

        return ChubbCatalogMapper.map_currencies(
            payload
        )

    def groupings(
        self,
        *,
        business_profile_name: str,
        agent_option_id: int,
    ) -> tuple[ChubbGrouping, ...]:
        """
        Consulta las agrupaciones disponibles para un
        Business Profile y un agente.

        Endpoint:
            GET /catalogs/groupings

        Query string:
            BusinessProfileName=<nombre>
            AgentOptionId=<id>
        """

        normalized_business_profile_name = (
            self._required_business_profile_name(
                business_profile_name
            )
        )

        normalized_agent_option_id = int(
            agent_option_id
        )

        if normalized_agent_option_id <= 0:
            raise ProviderInvalidResponseError(
                "agent_option_id debe ser un entero positivo."
            )

        params = {
            "BusinessProfileName": normalized_business_profile_name,
            "AgentOptionId": normalized_agent_option_id,
        }

        payload = self._get_catalog(
            "/catalogs/groupings",
            params=params,
        )

        return ChubbCatalogMapper.map_groupings(
            payload
        )

    def rates(
        self,
        *,
        grouping_id,
    ) -> tuple[ChubbRate, ...]:
        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="grouping_id",
        )

        payload = self._get_catalog(
            "/catalogs/rates",
            params={
                "GroupingId": grouping_id,
            },
        )

        return ChubbCatalogMapper.map_rates(payload)

    def payment_types(
        self,
        *,
        business_profile_id,
        grouping_id,
    ) -> tuple[ChubbPaymentType, ...]:
        business_profile_id = self._required_positive_int(
            business_profile_id,
            field_name="business_profile_id",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="grouping_id",
        )

        payload = self._get_catalog(
            "/catalogs/payment-types",
            params={
                "businessProfileId": business_profile_id,
                "groupingId": grouping_id,
            },
        )

        return ChubbCatalogMapper.map_payment_types(
            payload
        )

    def insured_amount_types(
        self,
        *,
        business_profile_name,
        rate_id,
        grouping_id,
    ) -> tuple[ChubbInsuredAmountType, ...]:
        business_profile_name = self._required_text(
            business_profile_name,
            field_name="business_profile_name",
        )

        rate_id = self._required_positive_int(
            rate_id,
            field_name="rate_id",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="grouping_id",
        )

        payload = self._get_catalog(
            "/catalogs/insured-amount/types",
            params={
                "BusinessProfileName": business_profile_name,
                "RateId": rate_id,
                "GroupingId": grouping_id,
            },
        )

        return ChubbCatalogMapper.map_insured_amount_types(
            payload
        )

    def packages(
        self,
        *,
        grouping_id,
        business_profile_name=None,
    ) -> tuple[ChubbPackage, ...]:
        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="GroupingId",
        )

        params = {
            "GroupingId": grouping_id,
        }

        if business_profile_name is not None:
            if not isinstance(business_profile_name, str):
                raise ProviderInvalidResponseError(
                    "BusinessProfileName debe ser una cadena."
                )

            business_profile_name = business_profile_name.strip()

            if business_profile_name:
                params["BusinessProfileName"] = business_profile_name

        payload = self._get_catalog(
            "/catalogs/packages",
            params=params,
        )

        return ChubbCatalogMapper.map_packages(payload)

    def vehicle_makes(
        self,
        *,
        business_profile_name: str,
        grouping_id: int,
        rate_id: int,
    ) -> tuple[ChubbVehicleMake, ...]:
        business_profile_name = self._required_text(
            business_profile_name,
            field_name="BusinessProfileName",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="GroupingId",
        )

        rate_id = self._required_positive_int(
            rate_id,
            field_name="RateId",
        )

        payload = self._get_catalog(
            "/catalogs/vehicles/makes",
            params={
                "BusinessProfileName": business_profile_name,
                "GroupingId": grouping_id,
                "RateId": rate_id,
            },
        )

        return ChubbCatalogMapper.map_vehicle_makes(payload)

    def vehicle_submakes(
        self,
        *,
        business_profile_name: str,
        make_id: int,
        grouping_id: int,
        rate_id: int,
    ) -> tuple[ChubbVehicleSubmake, ...]:
        business_profile_name = self._required_text(
            business_profile_name,
            field_name="BusinessProfileName",
        )

        make_id = self._required_positive_int(
            make_id,
            field_name="MakeId",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="GroupingId",
        )

        rate_id = self._required_positive_int(
            rate_id,
            field_name="RateId",
        )

        payload = self._get_catalog(
            "/catalogs/vehicles/submakes",
            params={
                "BusinessProfileName": (
                    business_profile_name
                ),
                "MakeId": make_id,
                "GroupingId": grouping_id,
                "RateId": rate_id,
            },
        )

        return ChubbCatalogMapper.map_vehicle_submakes(
            payload
        )

    def vehicle_types(
        self,
        *,
        business_profile_name: str,
        submake_id: int,
        grouping_id: int,
        rate_id: int,
    ) -> tuple[ChubbVehicleType, ...]:
        business_profile_name = self._required_text(
            business_profile_name,
            field_name="BusinessProfileName",
        )

        submake_id = self._required_positive_int(
            submake_id,
            field_name="SubMakeId",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="GroupingId",
        )

        rate_id = self._required_positive_int(
            rate_id,
            field_name="RateId",
        )

        payload = self._get_catalog(
            "/catalogs/vehicles/types",
            params={
                "BusinessProfileName": business_profile_name,
                "SubMakeId": submake_id,
                "GroupingId": grouping_id,
                "RateId": rate_id,
            },
        )

        return ChubbCatalogMapper.map_vehicle_types(payload)

    def vehicle_years(
        self,
        *,
        business_profile_name: str,
        vehicle_type_id: int,
        grouping_id: int,
        rate_id: int,
    ) -> tuple[ChubbVehicleYear, ...]:

        business_profile_name = self._required_text(
            business_profile_name,
            field_name="BusinessProfileName",
        )

        vehicle_type_id = self._required_positive_int(
            vehicle_type_id,
            field_name="VehicleTypeId",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="GroupingId",
        )

        rate_id = self._required_positive_int(
            rate_id,
            field_name="RateId",
        )

        payload = self._get_catalog(
            "/catalogs/vehicles/years",
            params={
                "BusinessProfileName": business_profile_name,
                "VehicleTypeId": vehicle_type_id,
                "GroupingId": grouping_id,
                "RateId": rate_id,
            },
        )

        return ChubbCatalogMapper.map_vehicle_years(
            payload
        )

    def vehicle_data(
        self,
        *,
        business_profile_name: str,
        grouping_id: int,
        rate_id: int,
        vehicle_year: int,
    ) -> tuple[ChubbVehicleData, ...]:
        business_profile_name = self._required_text(
            business_profile_name,
            field_name="BusinessProfileName",
        )

        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="GroupingId",
        )

        rate_id = self._required_positive_int(
            rate_id,
            field_name="RateId",
        )

        vehicle_year = self._required_positive_int(
            vehicle_year,
            field_name="VehicleYear",
        )

        payload = self._get_catalog(
            "/catalogs/vehicles/data",
            params={
                "BusinessProfileName": business_profile_name,
                "GroupingId": grouping_id,
                "RateId": rate_id,
                "VehicleYear": vehicle_year,
            },
        )

        return ChubbCatalogMapper.map_vehicle_data(payload)

    def vehicle_uses(
        self,
        *,
        grouping_id: int,
        country_subdivision_id: int,
        rate_id: int,
        use_id: int,
    ) -> tuple[ChubbVehicleUse, ...]:
        grouping_id = self._required_positive_int(
            grouping_id,
            field_name="grouping_id",
        )
        country_subdivision_id = self._required_positive_int(
            country_subdivision_id,
            field_name="country_subdivision_id",
        )
        rate_id = self._required_positive_int(
            rate_id,
            field_name="rate_id",
        )
        use_id = self._required_positive_int(
            use_id,
            field_name="use_id",
        )

        payload = self._get_catalog(
            "/catalogs/vehicles/uses",
            params={
                "GroupingId": grouping_id,
                "CountrySubdivisionId": country_subdivision_id,
                "RateId": rate_id,
                "UseId": use_id,
            },
        )

        return ChubbCatalogMapper.vehicle_uses(payload)
