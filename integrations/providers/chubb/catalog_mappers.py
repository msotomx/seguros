from collections.abc import Mapping, Sequence
from typing import Any

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
    ChubbCountrySubdivision,
    ChubbMunicipality,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


class ChubbCatalogMapper:
    """
    Convierte las respuestas de los catálogos de Chubb
    en contratos internos inmutables.

    No realiza llamadas HTTP.
    No consulta configuración del proveedor.
    """

    @staticmethod
    def _extract_agents_collection(
        payload: Mapping[str, Any],
    ) -> Sequence[Any]:
        possible_keys = (
            "agents",
            "agentOptions",
            "Agents",
            "AgentOptions",
        )

        for key in possible_keys:
            value = payload.get(key)

            if value is not None:
                if not isinstance(value, Sequence) or isinstance(
                    value,
                    (str, bytes),
                ):
                    raise ProviderInvalidResponseError(
                        f"El campo '{key}' no contiene "
                        "una lista válida."
                    )

                return value

        raise ProviderInvalidResponseError(
            "La respuesta de Chubb no contiene "
            "una colección de agentes válida."
        )

    @staticmethod
    def _first_present_value(
        data: Mapping[str, Any],
        *keys: str,
    ) -> Any:
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]

        return None

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

    @classmethod
    def map_business_profiles(
        cls,
        payload: Any,
    ) -> tuple[ChubbBusinessProfile, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Business Profiles "
                "debe ser un objeto JSON."
            )

        profiles = payload.get("businessProfiles")

        if not isinstance(profiles, Sequence) or isinstance(
            profiles,
            (str, bytes),
        ):
            raise ProviderInvalidResponseError(
                "La respuesta de Chubb no contiene "
                "'businessProfiles' válido."
            )

        results: list[ChubbBusinessProfile] = []

        for index, profile in enumerate(profiles):
            if not isinstance(profile, Mapping):
                raise ProviderInvalidResponseError(
                    "Business Profile inválido en la posición "
                    f"{index}."
                )

            business_profile_id = cls._required_positive_int(
                profile.get("businessProfileId"),
                field_name="businessProfileId",
            )

            name = cls._required_text(
                profile.get("businessProfileName"),
                field_name="businessProfileName",
            )

            description = str(
                profile.get(
                    "businessProfileDescription",
                    "",
                )
                or ""
            ).strip()

            results.append(
                ChubbBusinessProfile(
                    business_profile_id=business_profile_id,
                    name=name,
                    description=description,
                )
            )

        return tuple(results)

    @classmethod
    def map_agents(
        cls,
        payload: Any,
    ) -> tuple[ChubbAgent, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Agents debe ser un objeto JSON."
            )

        agents = cls._extract_agents_collection(payload)

        results: list[ChubbAgent] = []

        for index, agent in enumerate(agents):
            if not isinstance(agent, Mapping):
                raise ProviderInvalidResponseError(
                    "Agent inválido en la posición "
                    f"{index}."
                )

            agent_option_id = cls._required_positive_int(
                cls._first_present_value(
                    agent,
                    "agentOptionId",
                    "AgentOptionId",
                    "agentId",
                    "AgentId",
                ),
                field_name="agentOptionId",
            )

            name = cls._required_text(
                cls._first_present_value(
                    agent,
                    "agentName",
                    "AgentName",
                    "name",
                    "Name",
                    "description",
                    "Description",
                ),
                field_name="agentName",
            )

            description_value = cls._first_present_value(
                agent,
                "agentDescription",
                "AgentDescription",
                "description",
                "Description",
            )

            description = str(
                description_value or ""
            ).strip()

            results.append(
                ChubbAgent(
                    agent_option_id=agent_option_id,
                    name=name,
                    description=description,
                )
            )

        return tuple(results)
    
    @staticmethod
    def _extract_calculation_types_collection(
        payload: Mapping[str, Any],
    ) -> Sequence[Any]:
        possible_keys = (
            "calculationTypes",
            "calculationTypeOptions",
            "CalculationTypes",
            "CalculationTypeOptions",
        )

        for key in possible_keys:
            value = payload.get(key)

            if value is not None:
                if not isinstance(value, Sequence) or isinstance(
                    value,
                    (str, bytes),
                ):
                    raise ProviderInvalidResponseError(
                        f"El campo '{key}' no contiene "
                        "una lista válida."
                    )

                return value

        raise ProviderInvalidResponseError(
            "La respuesta de Chubb no contiene "
            "una colección de tipos de cálculo válida."
        )

    @classmethod
    def map_calculation_types(
        cls,
        payload: Any,
    ) -> tuple[ChubbCalculationType, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Calculation Types "
                "debe ser un objeto JSON."
            )

        calculation_types = (
            cls._extract_calculation_types_collection(
                payload
            )
        )

        results: list[ChubbCalculationType] = []

        for index, calculation_type in enumerate(
            calculation_types
        ):

            if not isinstance(calculation_type, Mapping):
                raise ProviderInvalidResponseError(
                    "Calculation Type inválido en la posición "
                    f"{index}."
                )

            calculation_type_id = cls._required_positive_int(
                cls._first_present_value(
                    calculation_type,
                    "calculationTypeId",
                    "CalculationTypeId",
                ),
                field_name="calculationTypeId",
            )

            description = cls._required_text(
                cls._first_present_value(
                    calculation_type,
                    "calculationTypeDescription",
                    "CalculationTypeDescription",
                ),
                field_name="calculationTypeDescription",
            )

            results.append(
                ChubbCalculationType(
                    calculation_type_id=calculation_type_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(results)

    @classmethod
    def map_conduits(
        cls,
        payload: Any,
    ) -> tuple[ChubbConduit, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Conduits "
                "debe ser un objeto JSON."
            )

        conduits = cls._extract_conduits_collection(
            payload
        )

        results: list[ChubbConduit] = []

        for index, conduit in enumerate(conduits):

            if not isinstance(conduit, Mapping):
                raise ProviderInvalidResponseError(
                    "Conduit inválido en la posición "
                    f"{index}."
                )

            conduit_id = cls._required_positive_int(
                cls._first_present_value(
                    conduit,
                    "conduitId",
                    "ConduitId",
                ),
                field_name="conduitId",
            )

            description = cls._required_text(
                cls._first_present_value(
                    conduit,
                    "conduitDescription",
                    "ConduitDescription",
                    "description",
                    "Description",
                ),
                field_name="conduitDescription",
            )

            results.append(
                ChubbConduit(
                    conduit_id=conduit_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(results)

    @classmethod
    def _extract_conduits_collection(
        cls,
        payload: Mapping[str, Any],
    ) -> Sequence[Any]:
        return cls._required_collection(
            cls._first_present_value(
                payload,
                "conduits",
                "Conduits",
            ),
            field_name="conduits",
        )

    @classmethod
    def map_currencies(
        cls,
        payload: Any,
    ) -> tuple[ChubbCurrency, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Currencies "
                "debe ser un objeto JSON."
            )

        currencies = (
            cls._extract_currencies_collection(
                payload
            )
        )

        results: list[ChubbCurrency] = []

        for index, currency in enumerate(
            currencies
        ):

            if not isinstance(currency, Mapping):
                raise ProviderInvalidResponseError(
                    "Currency inválida en la posición "
                    f"{index}."
                )

            currency_id = cls._required_positive_int(
                cls._first_present_value(
                    currency,
                    "currencyId",
                    "CurrencyId",
                ),
                field_name="currencyId",
            )

            description = cls._required_text(
                cls._first_present_value(
                    currency,
                    "currencyDescription",
                    "CurrencyDescription",
                ),
                field_name="currencyDescription",
            )

            results.append(
                ChubbCurrency(
                    currency_id=currency_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(results)

    @classmethod
    def _extract_currencies_collection(
        cls,
        payload: Mapping[str, Any],
    ) -> Sequence[Any]:
        currencies = cls._first_present_value(
            payload,
            "currencies",
            "Currencies",
        )

        if not isinstance(currencies, list):
            raise ProviderInvalidResponseError(
                "El campo currencies debe ser una lista."
            )

        return currencies

    @classmethod
    def map_groupings(
        cls,
        payload: Any,
    ) -> tuple[ChubbGrouping, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Groupings "
                "debe ser un objeto JSON."
            )

        groupings = cls._extract_groupings_collection(
            payload
        )

        results: list[ChubbGrouping] = []

        for index, grouping in enumerate(groupings):
            if not isinstance(grouping, Mapping):
                raise ProviderInvalidResponseError(
                    "Grouping inválido en la posición "
                    f"{index}."
                )

            grouping_id = cls._required_positive_int(
                cls._first_present_value(
                    grouping,
                    "groupingId",
                    "GroupingId",
                ),
                field_name="groupingId",
            )

            description = cls._required_text(
                cls._first_present_value(
                    grouping,
                    "groupingDescription",
                    "GroupingDescription",
                ),
                field_name="groupingDescription",
            )

            results.append(
                ChubbGrouping(
                    grouping_id=grouping_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(results)

    @classmethod
    def _extract_groupings_collection(
        cls,
        payload: Mapping[str, Any],
    ) -> Sequence[Any]:
        groupings = cls._first_present_value(
            payload,
            "groupings",
            "Groupings",
        )

        if not isinstance(groupings, list):
            raise ProviderInvalidResponseError(
                "El campo groupings debe ser una lista."
            )

        return groupings

    @classmethod
    def map_rates(
        cls,
        payload,
    ) -> tuple[ChubbRate, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Rates debe ser un objeto JSON."
            )

        rates = cls._extract_rates_collection(payload)

        mapped_rates = []

        for item in rates:
            if not isinstance(item, Mapping):
                raise ProviderInvalidResponseError(
                    "Cada elemento de rates debe ser un objeto JSON."
                )

            rate_id = cls._first_present_value(
                item,
                "rateId",
                "RateId",
            )

            description = cls._first_present_value(
                item,
                "rateDescription",
                "RateDescription",
            )

            rate_type_id = cls._first_present_value(
                item,
                "rateTypeId",
                "RateTypeId",
            )

            if (
                not isinstance(rate_id, int)
                or isinstance(rate_id, bool)
                or rate_id <= 0
            ):
                raise ProviderInvalidResponseError(
                    "El campo rateId debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ProviderInvalidResponseError(
                    "El campo rateDescription debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ProviderInvalidResponseError(
                    "El campo rateDescription no puede estar vacío."
                )

            if (
                not isinstance(rate_type_id, int)
                or isinstance(rate_type_id, bool)
                or rate_type_id <= 0
            ):
                raise ProviderInvalidResponseError(
                    "El campo rateTypeId debe ser un entero positivo."
                )

            mapped_rates.append(
                ChubbRate(
                    rate_id=rate_id,
                    name=description,
                    description=description,
                    rate_type_id=rate_type_id,
                )
            )

        return tuple(mapped_rates)

    @classmethod
    def _extract_rates_collection(
        cls,
        payload,
    ):
        rates = cls._first_present_value(
            payload,
            "rates",
            "Rates",
        )

        if not isinstance(rates, list):
            raise ProviderInvalidResponseError(
                "El campo rates debe ser una lista."
            )

        return rates

    @classmethod
    def map_payment_types(
        cls,
        payload,
    ) -> tuple[ChubbPaymentType, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Payment Types debe ser un objeto JSON."
            )

        payment_types = cls._extract_payment_types_collection(
            payload
        )

        mapped_payment_types = []

        for item in payment_types:
            if not isinstance(item, Mapping):
                raise ProviderInvalidResponseError(
                    "Cada elemento de paymentTypes debe ser un objeto JSON."
                )

            payment_type_id = cls._first_present_value(
                item,
                "paymentTypeId",
                "PaymentTypeId",
            )

            description = cls._first_present_value(
                item,
                "paymentTypeDescription",
                "PaymentTypeDescription",
            )

            if (
                not isinstance(payment_type_id, int)
                or isinstance(payment_type_id, bool)
                or payment_type_id <= 0
            ):
                raise ProviderInvalidResponseError(
                    "El campo paymentTypeId debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ProviderInvalidResponseError(
                    "El campo paymentTypeDescription debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ProviderInvalidResponseError(
                    "El campo paymentTypeDescription no puede estar vacío."
                )

            mapped_payment_types.append(
                ChubbPaymentType(
                    payment_type_id=payment_type_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(mapped_payment_types)

    @classmethod
    def _extract_payment_types_collection(
        cls,
        payload,
    ):
        payment_types = cls._first_present_value(
            payload,
            "paymentTypes",
            "PaymentTypes",
        )

        if not isinstance(payment_types, list):
            raise ProviderInvalidResponseError(
                "El campo paymentTypes debe ser una lista."
            )

        return payment_types

    @classmethod
    def map_insured_amount_types(
        cls,
        payload,
    ) -> tuple[ChubbInsuredAmountType, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Insured Amount Types debe ser un objeto JSON."
            )

        insured_amount_types = (
            cls._extract_insured_amount_types_collection(
                payload
            )
        )

        mapped_items = []

        for item in insured_amount_types:
            if not isinstance(item, Mapping):
                raise ProviderInvalidResponseError(
                    "Cada elemento de insuredAmountTypes debe ser un objeto JSON."
                )

            insured_amount_type_id = cls._first_present_value(
                item,
                "insuredAmountTypeId",
                "InsuredAmountTypeId",
            )

            description = cls._first_present_value(
                item,
                "insuredAmountTypeDescription",
                "InsuredAmountTypeDescription",
            )

            is_default = cls._first_present_value(
                item,
                "insuredAmountTypeDefault",
                "InsuredAmountTypeDefault",
            )

            vehicle_class_id = cls._first_present_value(
                item,
                "vehicleClassId",
                "VehicleClassId",
            )

            vehicle_condition_id = cls._first_present_value(
                item,
                "vehicleConditionId",
                "VehicleConditionId",
            )

            if (
                not isinstance(insured_amount_type_id, int)
                or isinstance(insured_amount_type_id, bool)
                or insured_amount_type_id <= 0
            ):
                raise ProviderInvalidResponseError(
                    "El campo insuredAmountTypeId debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ProviderInvalidResponseError(
                    "El campo insuredAmountTypeDescription debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ProviderInvalidResponseError(
                    "El campo insuredAmountTypeDescription no puede estar vacío."
                )

            if is_default is not None and not isinstance(
                is_default,
                bool,
            ):
                raise ProviderInvalidResponseError(
                    "El campo insuredAmountTypeDefault debe ser booleano o null."
                )

            if (
                not isinstance(vehicle_class_id, int)
                or isinstance(vehicle_class_id, bool)
                or vehicle_class_id <= 0
            ):
                raise ProviderInvalidResponseError(
                    "El campo vehicleClassId debe ser un entero positivo."
                )

            if (
                not isinstance(vehicle_condition_id, int)
                or isinstance(vehicle_condition_id, bool)
                or vehicle_condition_id < 0
            ):
                raise ProviderInvalidResponseError(
                    "El campo vehicleConditionId debe ser un entero no negativo."
                )

            mapped_items.append(
                ChubbInsuredAmountType(
                    insured_amount_type_id=insured_amount_type_id,
                    name=description,
                    description=description,
                    is_default=is_default,
                    vehicle_class_id=vehicle_class_id,
                    vehicle_condition_id=vehicle_condition_id,
                )
            )

        return tuple(mapped_items)

    @classmethod
    def _extract_insured_amount_types_collection(
        cls,
        payload,
    ):
        insured_amount_types = cls._first_present_value(
            payload,
            "insuredAmountTypes",
            "InsuredAmountTypes",
        )

        if not isinstance(insured_amount_types, list):
            raise ProviderInvalidResponseError(
                "El campo insuredAmountTypes debe ser una lista."
            )

        return insured_amount_types

    @classmethod
    def map_packages(
        cls,
        payload,
    ) -> tuple[ChubbPackage, ...]:
        packages = cls._extract_packages_collection(payload)

        mapped_packages = []

        for index, item in enumerate(packages):
            if not isinstance(item, Mapping):
                raise ProviderInvalidResponseError(
                    "Cada elemento de packages debe ser un objeto. "
                    f"Índice inválido: {index}."
                )

            package_id = item.get("packageId")
            description = item.get("packageDescription")

            if (
                isinstance(package_id, bool)
                or not isinstance(package_id, int)
                or package_id <= 0
            ):
                raise ProviderInvalidResponseError(
                    "packageId debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ProviderInvalidResponseError(
                    "packageDescription debe ser una cadena."
                )

            description = description.strip()

            if not description:
                raise ProviderInvalidResponseError(
                    "packageDescription no puede estar vacío."
                )

            mapped_packages.append(
                ChubbPackage(
                    package_id=package_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(mapped_packages)

    @classmethod
    def _extract_packages_collection(cls, payload):
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta del catálogo Packages debe ser un objeto."
            )

        packages = cls._first_present_value(
            payload,
            "packages",
            "Packages",
        )

        if not isinstance(packages, list):
            raise ProviderInvalidResponseError(
                "La respuesta del catálogo Packages debe contener "
                "una lista en packages."
            )

        return packages

    def map_vehicle_makes(payload: Any) -> tuple[ChubbVehicleMake, ...]:
        if not isinstance(payload, Mapping):
            raise ValueError(
                "La respuesta de Vehicles Makes debe ser un objeto JSON."
            )

        makes = payload.get("makes")

        if not isinstance(makes, list):
            raise ValueError(
                "El campo 'makes' debe ser una lista."
            )

        result: list[ChubbVehicleMake] = []

        for index, item in enumerate(makes):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"El elemento makes[{index}] debe ser un objeto JSON."
                )

            make_id = item.get("makeId")
            description = item.get("makeDescription")

            if (
                isinstance(make_id, bool)
                or not isinstance(make_id, int)
                or make_id <= 0
            ):
                raise ValueError(
                    f"makes[{index}].makeId debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ValueError(
                    f"makes[{index}].makeDescription debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ValueError(
                    f"makes[{index}].makeDescription no puede estar vacío."
                )

            result.append(
                ChubbVehicleMake(
                    make_id=make_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(result)

    @staticmethod
    def map_vehicle_submakes(
        payload: Any,
    ) -> tuple[ChubbVehicleSubmake, ...]:
        if not isinstance(payload, Mapping):
            raise ValueError(
                "La respuesta de Vehicle Submakes "
                "debe ser un objeto JSON."
            )

        submakes = payload.get("submake")

        if not isinstance(submakes, list):
            raise ValueError(
                "El campo 'submake' debe ser una lista."
            )

        result: list[ChubbVehicleSubmake] = []

        for index, item in enumerate(submakes):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"El elemento submake[{index}] "
                    "debe ser un objeto JSON."
                )

            submake_id = item.get("subMakeId")
            description = item.get(
                "subMakeDescription"
            )

            if (
                isinstance(submake_id, bool)
                or not isinstance(submake_id, int)
                or submake_id <= 0
            ):
                raise ValueError(
                    f"submake[{index}].subMakeId "
                    "debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ValueError(
                    f"submake[{index}]."
                    "subMakeDescription debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ValueError(
                    f"submake[{index}]."
                    "subMakeDescription no puede estar vacío."
                )

            result.append(
                ChubbVehicleSubmake(
                    submake_id=submake_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(result)

    @staticmethod
    def map_vehicle_types(
        payload: Any,
    ) -> tuple[ChubbVehicleType, ...]:
        if not isinstance(payload, Mapping):
            raise ValueError(
                "La respuesta de Vehicle Types debe ser un objeto JSON."
            )

        types = payload.get("types")

        if not isinstance(types, list):
            raise ValueError(
                "El campo 'types' debe ser una lista."
            )

        result: list[ChubbVehicleType] = []

        for index, item in enumerate(types):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"El elemento types[{index}] debe ser un objeto JSON."
                )

            vehicle_type_id = item.get("vehicleTypeId")
            description = item.get("vehicleTypeDescription")

            if (
                isinstance(vehicle_type_id, bool)
                or not isinstance(vehicle_type_id, int)
                or vehicle_type_id <= 0
            ):
                raise ValueError(
                    f"types[{index}].vehicleTypeId "
                    "debe ser un entero positivo."
                )

            if not isinstance(description, str):
                raise ValueError(
                    f"types[{index}].vehicleTypeDescription "
                    "debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ValueError(
                    f"types[{index}].vehicleTypeDescription "
                    "no puede estar vacío."
                )

            result.append(
                ChubbVehicleType(
                    vehicle_type_id=vehicle_type_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(result)

    @staticmethod
    def map_vehicle_years(
        payload: Any,
    ) -> tuple[ChubbVehicleYear, ...]:
        if not isinstance(payload, Mapping):
            raise ValueError(
                "La respuesta de Vehicle Years debe ser un objeto JSON."
            )

        years = payload.get("years")

        if not isinstance(years, list):
            raise ValueError(
                "El campo 'years' debe ser una lista."
            )

        result: list[ChubbVehicleYear] = []

        for index, item in enumerate(years):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"El elemento years[{index}] debe ser un objeto JSON."
                )

            year = item.get("year")
            description = item.get("yearDescription")

            if (
                isinstance(year, bool)
                or not isinstance(year, int)
                or year <= 1900
            ):
                raise ValueError(
                    f"years[{index}].year debe ser un entero válido."
                )

            if not isinstance(description, str):
                raise ValueError(
                    f"years[{index}].yearDescription debe ser texto."
                )

            description = description.strip()

            if not description:
                raise ValueError(
                    f"years[{index}].yearDescription no puede estar vacío."
                )

            result.append(
                ChubbVehicleYear(
                    year=year,
                    name=description,
                    description=description,
                )
            )

        return tuple(result)

    @staticmethod
    def map_vehicle_data(
        payload: Any,
    ) -> tuple[ChubbVehicleData, ...]:
        if not isinstance(payload, Mapping):
            raise ValueError(
                "La respuesta de Vehicle Data debe ser un objeto JSON."
            )

        vehicles = payload.get("vehicles")

        if not isinstance(vehicles, list):
            raise ValueError(
                "El campo 'vehicles' debe ser una lista."
            )

        result: list[ChubbVehicleData] = []

        for index, item in enumerate(vehicles):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"El elemento vehicles[{index}] "
                    "debe ser un objeto JSON."
                )

            def required_int(
                field_name: str,
                *,
                allow_zero: bool = False,
            ) -> int:
                value = item.get(field_name)

                minimum = 0 if allow_zero else 1

                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < minimum
                ):
                    qualifier = (
                        "un entero mayor o igual a cero"
                        if allow_zero
                        else "un entero positivo"
                    )

                    raise ValueError(
                        f"vehicles[{index}].{field_name} "
                        f"debe ser {qualifier}."
                    )

                return value

            def required_text(field_name: str) -> str:
                value = item.get(field_name)

                if not isinstance(value, str):
                    raise ValueError(
                        f"vehicles[{index}].{field_name} "
                        "debe ser texto."
                    )

                value = value.strip()

                if not value:
                    raise ValueError(
                        f"vehicles[{index}].{field_name} "
                        "no puede estar vacío."
                    )

                return value

            tonnage = item.get("tonnage")

            if (
                isinstance(tonnage, bool)
                or not isinstance(tonnage, (int, float))
                or tonnage < 0
            ):
                raise ValueError(
                    f"vehicles[{index}].tonnage "
                    "debe ser un número mayor o igual a cero."
                )

            active = item.get("active")

            if not isinstance(active, bool):
                raise ValueError(
                    f"vehicles[{index}].active "
                    "debe ser booleano."
                )

            result.append(
                ChubbVehicleData(
                    vehicle_id=required_int("vehicleId"),
                    description=required_text(
                        "vehicleDescription"
                    ),
                    vehicle_type_id=required_int(
                        "vehicleTypeId"
                    ),
                    trailer_id=required_int("trailerId"),
                    tonnage_id=required_int("tonnageId"),
                    short_description=required_text(
                        "shortDescription"
                    ),
                    long_description=required_text(
                        "longDescription"
                    ),
                    tonnage=float(tonnage),
                    passengers=required_int(
                        "passengers",
                        allow_zero=True,
                    ),
                    cmst=required_text("cmst"),
                    cmst_consecutive=required_int(
                        "cmstConsecutive"
                    ),
                    active=active,
                    status=required_int("status"),
                    make_id=required_int("makeId"),
                    submake_id=required_int("subMakeId"),
                    vehicle_type_description=required_text(
                        "vehicleTypeDescription"
                    ),
                    trailer_type_description=required_text(
                        "trailerTypeDescription"
                    ),
                    submake_description=required_text(
                        "subMakeDescription"
                    ),
                    make_description=required_text(
                        "makeDescription"
                    ),
                    tonnage_description=required_text(
                        "tonnageDescription"
                    ),
                    class_id=required_int("classId"),
                    vehicle_group_id=required_int(
                        "vehicleGroupId"
                    ),
                    vehicle_group_description=required_text(
                        "vehicleGroupDescription"
                    ),
                    status_description=required_text(
                        "statusDescription"
                    ),
                    mtc=required_text("mtc"),
                    vehicle_key=required_text("vehicleKey"),
                    vehicle_condition_id=required_int(
                        "vehicleConditionId",
                        allow_zero=True,
                    ),
                )
            )

        return tuple(result)

    @staticmethod
    def vehicle_uses(payload):
        if not isinstance(payload, Mapping):
            raise ValueError(
                "Vehicle uses payload must be a mapping."
            )

        items = payload.get("servicesUses")

        if not isinstance(items, list):
            raise ValueError(
                "Vehicle uses collection must be a list."
            )

        results = []

        for item in items:
            if not isinstance(item, Mapping):
                raise ValueError(
                    "Vehicle use item must be a mapping."
                )

            service_id = item.get("serviceId")
            service_description = item.get(
                "serviceDescription"
            )
            use_id = item.get("useId")
            use_description = item.get(
                "useDescription"
            )

            if (
                isinstance(service_id, bool)
                or not isinstance(service_id, int)
                or service_id <= 0
            ):
                raise ValueError(
                    "serviceId must be a positive integer."
                )

            if not isinstance(
                service_description,
                str,
            ):
                raise ValueError(
                    "serviceDescription must be a string."
                )

            service_description = (
                service_description.strip()
            )

            if not service_description:
                raise ValueError(
                    "serviceDescription cannot be empty."
                )

            if (
                isinstance(use_id, bool)
                or not isinstance(use_id, int)
                or use_id <= 0
            ):
                raise ValueError(
                    "useId must be a positive integer."
                )

            if not isinstance(use_description, str):
                raise ValueError(
                    "useDescription must be a string."
                )

            use_description = use_description.strip()

            if not use_description:
                raise ValueError(
                    "useDescription cannot be empty."
                )

            results.append(
                ChubbVehicleUse(
                    service_id=service_id,
                    service_description=(
                        service_description
                    ),
                    use_id=use_id,
                    use_description=use_description,
                )
            )

        return tuple(results)

    @classmethod
    def map_country_subdivisions(
        cls,
        payload: Any,
    ) -> tuple[ChubbCountrySubdivision, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Country Subdivisions "
                "debe ser un objeto JSON."
            )

        items = payload.get("countrySubdivisions")

        if not isinstance(items, list):
            raise ProviderInvalidResponseError(
                "El campo 'countrySubdivisions' "
                "debe ser una lista."
            )

        results: list[ChubbCountrySubdivision] = []

        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise ProviderInvalidResponseError(
                    f"El elemento countrySubdivisions[{index}] "
                    "debe ser un objeto JSON."
                )

            subdivision_id = cls._required_positive_int(
                item.get("countrySubdivisionId"),
                field_name="countrySubdivisionId",
            )

            description = cls._required_text(
                item.get("countrySubdivisionDescription"),
                field_name="countrySubdivisionDescription",
            )

            results.append(
                ChubbCountrySubdivision(
                    subdivision_id=subdivision_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(results)

    @classmethod
    def map_municipalities(
        cls,
        payload: Any,
    ) -> tuple[ChubbMunicipality, ...]:
        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de Municipalities debe ser "
                "un objeto JSON."
            )

        items = payload.get("municipalities")

        if not isinstance(items, list):
            raise ProviderInvalidResponseError(
                "El campo 'municipalities' debe ser una lista."
            )

        results: list[ChubbMunicipality] = []

        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise ProviderInvalidResponseError(
                    f"El elemento municipalities[{index}] "
                    "debe ser un objeto JSON."
                )

            municipality_id = cls._required_positive_int(
                item.get("municipalityId"),
                field_name="municipalityId",
            )

            description = cls._required_text(
                item.get("municipalityDescription"),
                field_name="municipalityDescription",
            )

            results.append(
                ChubbMunicipality(
                    municipality_id=municipality_id,
                    name=description,
                    description=description,
                )
            )

        return tuple(results)
