from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)
from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
)
from integrations.providers.exceptions import (
    ProviderConfigurationError,
    ProviderInvalidResponseError,
)
from integrations.providers.chubb.contracts import (
    ChubbAgent,
    ChubbBusinessProfile,
    ChubbCalculationType,
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

class ChubbCatalogClientTest(SimpleTestCase):
    def setUp(self):
        self.configuration = SimpleNamespace(
            base_url=(
                "https://sit.example.com/"
                "digital.quote.partners"
            ),
            api_version="1",
            timeout=20,
            settings={
                "SYSTEM_NAME": "SEMI",
            },
        )

        self.configuration_service = Mock()
        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.auth_client = Mock()
        self.token = ChubbAccessToken(
            access_token="test-token",
            token_type="Bearer",
            expires_in=3599,
        )
        self.auth_client.get_token.return_value = (
            self.token
        )

        self.http_client = Mock()

        self.client = ChubbCatalogClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

    def test_business_profiles_executes_request(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "businessProfiles": [
                        {
                            "businessProfileId": 7195,
                            "businessProfileName": "BASE_TOM",
                            "businessProfileDescription": (
                                "BASE_TOM"
                            ),
                        }
                    ]
                },
                headers={},
            )
        )

        profiles = self.client.business_profiles()

        self.assertEqual(len(profiles), 1)

        profile = profiles[0]

        self.assertEqual(
            profile.business_profile_id,
            7195,
        )
        self.assertEqual(
            profile.name,
            "BASE_TOM",
        )
        self.assertEqual(
            profile.description,
            "BASE_TOM",
        )

        self.auth_client.get_token.assert_called_once_with()

        self.http_client.get.assert_called_once_with(
            "/catalogs/business-profiles",
            token=self.token,
            params={
                "SystemName": "SEMI",
            },
        )

    def test_loads_active_configuration(self):
        self.configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

    def test_rejects_missing_system_name(self):
        self.configuration.settings = {}

        with self.assertRaises(
            ProviderConfigurationError
        ):
            self.client.business_profiles()

        self.auth_client.get_token.assert_not_called()
        self.http_client.get.assert_not_called()

    def test_returns_empty_tuple(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "businessProfiles": [],
                },
                headers={},
            )
        )

        profiles = self.client.business_profiles()

        self.assertEqual(profiles, ())

    def test_rejects_invalid_payload(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data=[],
                headers={},
            )
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.business_profiles()

    def test_rejects_invalid_profile_id(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "businessProfiles": [
                        {
                            "businessProfileId": 0,
                            "businessProfileName": "BASE_TOM",
                            "businessProfileDescription": (
                                "BASE_TOM"
                            ),
                        }
                    ]
                },
                headers={},
            )
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.business_profiles()

    def test_agents_executes_request(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "agents": [
                        {
                            "agentOptionId": 150,
                            "agentName": "AGENTE PRUEBA",
                            "agentDescription": (
                                "Agente de Chubb SIT"
                            ),
                        }
                    ]
                },
                headers={},
            )
        )

        agents = self.client.agents(
            business_profile_name="BASE_TOM",
        )

        self.assertEqual(len(agents), 1)

        agent = agents[0]

        self.assertEqual(
            agent.agent_option_id,
            150,
        )
        self.assertEqual(
            agent.name,
            "AGENTE PRUEBA",
        )
        self.assertEqual(
            agent.description,
            "Agente de Chubb SIT",
        )

        self.auth_client.get_token.assert_called_once_with()

        self.http_client.get.assert_called_once_with(
            "/catalogs/agents",
            token=self.token,
            params={
                "BusinessProfileName": "BASE_TOM",
            },
        )


    def test_agents_normalizes_business_profile_name(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "agents": [],
                },
                headers={},
            )
        )

        agents = self.client.agents(
            business_profile_name="  BASE_TOM  ",
        )

        self.assertEqual(agents, ())

        self.http_client.get.assert_called_once_with(
            "/catalogs/agents",
            token=self.token,
            params={
                "BusinessProfileName": "BASE_TOM",
            },
        )


    def test_agents_accepts_agent_options_collection(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "agentOptions": [
                        {
                            "AgentOptionId": 150,
                            "AgentName": "AGENTE PRUEBA",
                            "Description": "Descripción",
                        }
                    ]
                },
                headers={},
            )
        )

        agents = self.client.agents(
            business_profile_name="BASE_TOM",
        )

        self.assertEqual(len(agents), 1)
        self.assertEqual(
            agents[0].agent_option_id,
            150,
        )


    def test_agents_rejects_empty_business_profile_name(self):
        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.agents(
                business_profile_name=" ",
            )

        self.auth_client.get_token.assert_not_called()
        self.http_client.get.assert_not_called()


    def test_agents_rejects_missing_collection(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "unexpected": [],
                },
                headers={},
            )
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.agents(
                business_profile_name="BASE_TOM",
            )

    def test_agents_rejects_invalid_agent_id(self):
        self.http_client.get.return_value = (
            SimpleNamespace(
                status_code=200,
                data={
                    "agents": [
                        {
                            "agentOptionId": 0,
                            "agentName": "AGENTE PRUEBA",
                        }
                    ]
                },
                headers={},
            )
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.agents(
                business_profile_name="BASE_TOM",
            )

    def test_calculation_types_returns_mapped_contracts(
        self,
    ):
        self.auth_client.get_token.return_value = (
            "access-token"
        )

        self.http_client.get.return_value.data = {
            "calculationTypes": [
                {
                    "calculationTypeId": 2,
                    "calculationTypeDescription": "CORTO PLAZO       ",
                },
                {
                    "calculationTypeId": 1,
                    "calculationTypeDescription": "PRORRATA          ",
                },
            ]
        }

        client = self.client

        results = self.client.calculation_types(
            business_profile_name="BASE_TOM",
            agent_option_id=91840,
        )

        self.assertEqual(len(results), 2)

        self.assertEqual(
            results[0].calculation_type_id,
            2,
        )
        self.assertEqual(
            results[0].name,
            "CORTO PLAZO",
        )
        self.assertEqual(
            results[0].description,
            "CORTO PLAZO",
        )
        self.assertEqual(
            results[1].calculation_type_id,
            1,
        )
        self.assertEqual(
            results[1].name,
            "PRORRATA",
        )        

        self.auth_client.get_token.assert_called_once_with()

        self.http_client.get.assert_called_once_with(
            "/catalogs/calculation-types",
            token="access-token",
            params={
                "BusinessProfileName": "BASE_TOM",
                "AgentOptionId": 91840,
            },
        )

    def test_calculation_types_normalizes_business_profile_name(
        self,
    ):
        self.auth_client.get_token.return_value = (
            "access-token"
        )

        self.http_client.get.return_value.data = {
            "calculationTypes": []
        }

        client = self.client

        results = self.client.calculation_types(
            business_profile_name="  BASE_TOM  ",
            agent_option_id=91840,
        )

        self.assertEqual(results, ())

        self.http_client.get.assert_called_once_with(
            "/catalogs/calculation-types",
            token="access-token",
            params={
                "BusinessProfileName": "BASE_TOM",
                "AgentOptionId": 91840,
            },
        )

    def test_calculation_types_rejects_empty_business_profile_name(
        self,
    ):
        client = self.client

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            client.calculation_types(
                business_profile_name="   ",
                agent_option_id=91840,
            )

        self.auth_client.get_token.assert_not_called()
        self.http_client.get.assert_not_called()
                        
    def test_calculation_types_rejects_invalid_payload(
        self,
    ):
        self.auth_client.get_token.return_value = (
            "access-token"
        )

        self.http_client.get.return_value.data = []

        client = self.client

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            client.calculation_types(
                business_profile_name="BASE_TOM",
                agent_option_id=91840,
            )

    def test_calculation_types_rejects_invalid_id(
        self,
    ):
        self.auth_client.get_token.return_value = (
            "access-token"
        )

        self.http_client.get.return_value.data = {
            "calculationTypes": [
                {
                    "calculationTypeId": 0,
                    "calculationTypeDescription": "CORTO PLAZO",
                }
            ]
        }

        client = self.client

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            client.calculation_types(
                business_profile_name="BASE_TOM",
                agent_option_id=91840,
            )

    def test_currencies_returns_mapped_contracts(self):
        payload = {
            "currencies": [
                {
                    "currencyId": 2,
                    "currencyDescription": "DOLARES           ",
                },
                {
                    "currencyId": 1,
                    "currencyDescription": "NACIONAL",
                },
            ]
        }

        self.client._get_catalog = Mock(
            return_value=payload
        )

        result = self.client.currencies(
            business_profile_name="BASE_TOM",
        )

        self.assertEqual(
            result,
            (
                ChubbCurrency(
                    currency_id=2,
                    name="DOLARES",
                    description="DOLARES",
                ),
                ChubbCurrency(
                    currency_id=1,
                    name="NACIONAL",
                    description="NACIONAL",
                ),
            ),
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/currencies",
            params={
                "BusinessProfileName": "BASE_TOM",
            },
        )


    def test_currencies_normalizes_business_profile_name(self):
        self.client._get_catalog = Mock(
            return_value={
                "currencies": [],
            }
        )

        result = self.client.currencies(
            business_profile_name="  base_tom  ",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/currencies",
            params={
                "BusinessProfileName": "base_tom",
            },
        )

    def test_currencies_rejects_empty_business_profile_name(self):
        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.currencies(
                business_profile_name="   ",
            )

        self.http_client.get_json.assert_not_called()


    def test_currencies_rejects_invalid_payload(self):
        #self.http_client.get_json.return_value = []
        self.client._get_catalog = Mock(
                return_value=[]
            )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.currencies(
                business_profile_name="BASE_TOM",
            )


    def test_currencies_rejects_invalid_id(self):
        self.client._get_catalog = Mock(
            return_value={

                "currencies": [
                    {
                        "currencyId": 0,
                        "currencyDescription": "NACIONAL",
                    }
                ]
            }
        )
        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.currencies(
                business_profile_name="BASE_TOM",
            )

    def test_groupings_returns_mapped_contracts(self):
        payload = {
            "groupings": [
                {
                    "groupingId": 353991,
                    "groupingDescription": "LUCRECIA_TEST",
                },
                {
                    "groupingId": 214070,
                    "groupingDescription": "PRUEBAMONI1",
                },
            ]
        }

        self.client._get_catalog = Mock(
            return_value=payload
        )

        result = self.client.groupings(
            business_profile_name="BASE_TOM",
            agent_option_id=91840,
        )

        self.assertEqual(
            result,
            (
                ChubbGrouping(
                    grouping_id=353991,
                    name="LUCRECIA_TEST",
                    description="LUCRECIA_TEST",
                ),
                ChubbGrouping(
                    grouping_id=214070,
                    name="PRUEBAMONI1",
                    description="PRUEBAMONI1",
                ),
            ),
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/groupings",
            params={
                "BusinessProfileName": "BASE_TOM",
                "AgentOptionId": 91840,
            },
        )


    def test_groupings_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "groupings": [],
            }
        )

        result = self.client.groupings(
            business_profile_name="  base_tom  ",
            agent_option_id="91840",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/groupings",
            params={
                "BusinessProfileName": "base_tom",
                "AgentOptionId": 91840,
            },
        )


    def test_groupings_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="   ",
                agent_option_id=91840,
            )

        self.client._get_catalog.assert_not_called()


    def test_groupings_rejects_zero_agent_option_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="BASE_TOM",
                agent_option_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_groupings_rejects_negative_agent_option_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="BASE_TOM",
                agent_option_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_groupings_rejects_invalid_payload(self):
        self.client._get_catalog = Mock(
            return_value=[]
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="BASE_TOM",
                agent_option_id=91840,
            )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/groupings",
            params={
                "BusinessProfileName": "BASE_TOM",
                "AgentOptionId": 91840,
            },
        )


    def test_groupings_rejects_invalid_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "groupings": "invalid",
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="BASE_TOM",
                agent_option_id=91840,
            )


    def test_groupings_rejects_invalid_grouping_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "groupings": [
                    {
                        "groupingId": 0,
                        "groupingDescription": "LUCRECIA_TEST",
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="BASE_TOM",
                agent_option_id=91840,
            )


    def test_groupings_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "groupings": [
                    {
                        "groupingId": 353991,
                        "groupingDescription": "   ",
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.groupings(
                business_profile_name="BASE_TOM",
                agent_option_id=91840,
            )
            
    def test_rates_returns_mapped_contracts(self):
        payload = {
            "rates": [
                {
                    "rateId": 1472,
                    "rateDescription": "1472",
                    "rateTypeId": 1,
                },
                {
                    "rateId": 511,
                    "rateDescription": "511",
                    "rateTypeId": 1,
                },
                {
                    "rateId": 308,
                    "rateDescription": "308",
                    "rateTypeId": 1,
                },
                {
                    "rateId": 171,
                    "rateDescription": "171",
                    "rateTypeId": 1,
                },
            ]
        }

        self.client._get_catalog = Mock(
            return_value=payload
        )

        result = self.client.rates(
            grouping_id=353991,
        )

        self.assertEqual(
            result,
            (
                ChubbRate(
                    rate_id=1472,
                    name="1472",
                    description="1472",
                    rate_type_id=1,
                ),
                ChubbRate(
                    rate_id=511,
                    name="511",
                    description="511",
                    rate_type_id=1,
                ),
                ChubbRate(
                    rate_id=308,
                    name="308",
                    description="308",
                    rate_type_id=1,
                ),
                ChubbRate(
                    rate_id=171,
                    name="171",
                    description="171",
                    rate_type_id=1,
                ),
            ),
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/rates",
            params={
                "GroupingId": 353991,
            },
        )


    def test_rates_normalizes_grouping_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "rates": [],
            }
        )

        result = self.client.rates(
            grouping_id="353991",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/rates",
            params={
                "GroupingId": 353991,
            },
        )


    def test_rates_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_rates_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_rates_rejects_invalid_payload(self):
        self.client._get_catalog = Mock(
            return_value=[]
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=353991,
            )


    def test_rates_rejects_invalid_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "rates": "invalid",
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=353991,
            )


    def test_rates_rejects_invalid_rate_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "rates": [
                    {
                        "rateId": 0,
                        "rateDescription": "1472",
                        "rateTypeId": 1,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=353991,
            )


    def test_rates_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "rates": [
                    {
                        "rateId": 1472,
                        "rateDescription": "   ",
                        "rateTypeId": 1,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=353991,
            )


    def test_rates_rejects_invalid_rate_type_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "rates": [
                    {
                        "rateId": 1472,
                        "rateDescription": "1472",
                        "rateTypeId": 0,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.rates(
                grouping_id=353991,
            )

    def test_payment_types_returns_mapped_contracts(self):
        payload = {
            "paymentTypes": [
                {
                    "paymentTypeId": 51,
                    "paymentTypeDescription": " CONTADO DLLS",
                },
                {
                    "paymentTypeId": 40,
                    "paymentTypeDescription": "ANUAL EXTENDIDA   ",
                },
                {
                    "paymentTypeId": 873,
                    "paymentTypeDescription": "Anual.",
                },
            ]
        }

        self.client._get_catalog = Mock(
            return_value=payload
        )

        result = self.client.payment_types(
            business_profile_id=7195,
            grouping_id=353991,
        )

        self.assertEqual(
            result,
            (
                ChubbPaymentType(
                    payment_type_id=51,
                    name="CONTADO DLLS",
                    description="CONTADO DLLS",
                ),
                ChubbPaymentType(
                    payment_type_id=40,
                    name="ANUAL EXTENDIDA",
                    description="ANUAL EXTENDIDA",
                ),
                ChubbPaymentType(
                    payment_type_id=873,
                    name="Anual.",
                    description="Anual.",
                ),
            ),
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/payment-types",
            params={
                "businessProfileId": 7195,
                "groupingId": 353991,
            },
        )


    def test_payment_types_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "paymentTypes": [],
            }
        )

        result = self.client.payment_types(
            business_profile_id="7195",
            grouping_id="353991",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/payment-types",
            params={
                "businessProfileId": 7195,
                "groupingId": 353991,
            },
        )


    def test_payment_types_rejects_zero_business_profile_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=0,
                grouping_id=353991,
            )

        self.client._get_catalog.assert_not_called()


    def test_payment_types_rejects_negative_business_profile_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=-1,
                grouping_id=353991,
            )

        self.client._get_catalog.assert_not_called()


    def test_payment_types_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=7195,
                grouping_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_payment_types_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=7195,
                grouping_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_payment_types_rejects_invalid_payload(self):
        self.client._get_catalog = Mock(
            return_value=[]
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=7195,
                grouping_id=353991,
            )


    def test_payment_types_rejects_invalid_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "paymentTypes": "invalid",
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=7195,
                grouping_id=353991,
            )


    def test_payment_types_rejects_invalid_payment_type_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "paymentTypes": [
                    {
                        "paymentTypeId": 0,
                        "paymentTypeDescription": "CONTADO",
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=7195,
                grouping_id=353991,
            )


    def test_payment_types_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "paymentTypes": [
                    {
                        "paymentTypeId": 12,
                        "paymentTypeDescription": "   ",
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.payment_types(
                business_profile_id=7195,
                grouping_id=353991,
            )

    def test_insured_amount_types_returns_mapped_contracts(self):
        payload = {
            "insuredAmountTypes": [
                {
                    "insuredAmountTypeId": 1,
                    "insuredAmountTypeDescription": " VALOR COMERCIAL ",
                    "insuredAmountTypeDefault": None,
                    "vehicleClassId": 1,
                    "vehicleConditionId": 0,
                },
                {
                    "insuredAmountTypeId": 2,
                    "insuredAmountTypeDescription": "VALOR CONVENIDO",
                    "insuredAmountTypeDefault": True,
                    "vehicleClassId": 2,
                    "vehicleConditionId": 1,
                },
            ]
        }

        self.client._get_catalog = Mock(
            return_value=payload
        )

        result = self.client.insured_amount_types(
            business_profile_name="BASE_TOM",
            rate_id=1472,
            grouping_id=353991,
        )

        self.assertEqual(
            result,
            (
                ChubbInsuredAmountType(
                    insured_amount_type_id=1,
                    name="VALOR COMERCIAL",
                    description="VALOR COMERCIAL",
                    is_default=None,
                    vehicle_class_id=1,
                    vehicle_condition_id=0,
                ),
                ChubbInsuredAmountType(
                    insured_amount_type_id=2,
                    name="VALOR CONVENIDO",
                    description="VALOR CONVENIDO",
                    is_default=True,
                    vehicle_class_id=2,
                    vehicle_condition_id=1,
                ),
            ),
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/insured-amount/types",
            params={
                "BusinessProfileName": "BASE_TOM",
                "RateId": 1472,
                "GroupingId": 353991,
            },
        )

    def test_insured_amount_types_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [],
            }
        )

        result = self.client.insured_amount_types(
            business_profile_name="  BASE_TOM  ",
            rate_id="1472",
            grouping_id="353991",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/insured-amount/types",
            params={
                "BusinessProfileName": "BASE_TOM",
                "RateId": 1472,
                "GroupingId": 353991,
            },
        )


    def test_insured_amount_types_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="   ",
                rate_id=1472,
                grouping_id=353991,
            )

        self.client._get_catalog.assert_not_called()


    def test_insured_amount_types_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=0,
                grouping_id=353991,
            )

        self.client._get_catalog.assert_not_called()


    def test_insured_amount_types_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=-1,
                grouping_id=353991,
            )

        self.client._get_catalog.assert_not_called()


    def test_insured_amount_types_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_insured_amount_types_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_insured_amount_types_rejects_invalid_payload(self):
        self.client._get_catalog = Mock(
            return_value=[]
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_rejects_invalid_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": "invalid",
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_rejects_invalid_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    "invalid",
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_rejects_invalid_type_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    {
                        "insuredAmountTypeId": 0,
                        "insuredAmountTypeDescription": (
                            "VALOR COMERCIAL"
                        ),
                        "insuredAmountTypeDefault": None,
                        "vehicleClassId": 1,
                        "vehicleConditionId": 0,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    {
                        "insuredAmountTypeId": 1,
                        "insuredAmountTypeDescription": "   ",
                        "insuredAmountTypeDefault": None,
                        "vehicleClassId": 1,
                        "vehicleConditionId": 0,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_rejects_invalid_default(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    {
                        "insuredAmountTypeId": 1,
                        "insuredAmountTypeDescription": (
                            "VALOR COMERCIAL"
                        ),
                        "insuredAmountTypeDefault": "true",
                        "vehicleClassId": 1,
                        "vehicleConditionId": 0,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_rejects_invalid_vehicle_class_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    {
                        "insuredAmountTypeId": 1,
                        "insuredAmountTypeDescription": (
                            "VALOR COMERCIAL"
                        ),
                        "insuredAmountTypeDefault": None,
                        "vehicleClassId": 0,
                        "vehicleConditionId": 0,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )


    def test_insured_amount_types_accepts_zero_vehicle_condition_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    {
                        "insuredAmountTypeId": 1,
                        "insuredAmountTypeDescription": (
                            "VALOR COMERCIAL"
                        ),
                        "insuredAmountTypeDefault": None,
                        "vehicleClassId": 1,
                        "vehicleConditionId": 0,
                    }
                ]
            }
        )

        result = self.client.insured_amount_types(
            business_profile_name="BASE_TOM",
            rate_id=1472,
            grouping_id=353991,
        )

        self.assertEqual(
            result,
            (
                ChubbInsuredAmountType(
                    insured_amount_type_id=1,
                    name="VALOR COMERCIAL",
                    description="VALOR COMERCIAL",
                    is_default=None,
                    vehicle_class_id=1,
                    vehicle_condition_id=0,
                ),
            ),
        )


    def test_insured_amount_types_rejects_negative_vehicle_condition_id(
        self,
    ):
        self.client._get_catalog = Mock(
            return_value={
                "insuredAmountTypes": [
                    {
                        "insuredAmountTypeId": 1,
                        "insuredAmountTypeDescription": (
                            "VALOR COMERCIAL"
                        ),
                        "insuredAmountTypeDefault": None,
                        "vehicleClassId": 1,
                        "vehicleConditionId": -1,
                    }
                ]
            }
        )

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.insured_amount_types(
                business_profile_name="BASE_TOM",
                rate_id=1472,
                grouping_id=353991,
            )

    def test_packages_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "packages": [],
            }
        )

        result = self.client.packages(
            business_profile_name="  BASE_TOM  ",
            grouping_id="353991",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/packages",
            params={
                "BusinessProfileName": "BASE_TOM",
                "GroupingId": 353991,
            },
        )

    def test_packages_accepts_empty_business_profile_name(self):
        self.client._get_catalog = Mock(
            return_value={
                "packages": [],
            }
        )

        result = self.client.packages(
            business_profile_name="   ",
            grouping_id=353991,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/packages",
            params={
                "GroupingId": 353991,
            },
        )

    def test_packages_returns_mapped_contracts(self):
        self.client._get_catalog = Mock(
            return_value={
                "packages": [
                    {
                        "packageId": 1,
                        "packageDescription": " AMPLIA ",
                    },
                    {
                        "packageId": 2,
                        "packageDescription": "LIMITADA",
                    },
                    {
                        "packageId": 3,
                        "packageDescription": "RC",
                    },
                ]
            }
        )

        result = self.client.packages(
            grouping_id=353991,
        )

        self.assertEqual(
            result,
            (
                ChubbPackage(
                    package_id=1,
                    name="AMPLIA",
                    description="AMPLIA",
                ),
                ChubbPackage(
                    package_id=2,
                    name="LIMITADA",
                    description="LIMITADA",
                ),
                ChubbPackage(
                    package_id=3,
                    name="RC",
                    description="RC",
                ),
            ),
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/packages",
            params={
                "GroupingId": 353991,
            },
        )

    def test_packages_omits_empty_business_profile_name(self):
        self.client._get_catalog = Mock(
            return_value={
                "packages": [],
            }
        )

        result = self.client.packages(
            grouping_id=353991,
            business_profile_name="   ",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/packages",
            params={
                "GroupingId": 353991,
            },
        )

    def test_packages_includes_business_profile_name_when_provided(self):
        self.client._get_catalog = Mock(
            return_value={
                "packages": [],
            }
        )

        result = self.client.packages(
            grouping_id="353991",
            business_profile_name="  BASE_TOM  ",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/packages",
            params={
                "GroupingId": 353991,
                "BusinessProfileName": "BASE_TOM",
            },
        )

    def test_packages_omits_none_business_profile_name(self):
        self.client._get_catalog = Mock(
            return_value={
                "packages": [],
            }
        )

        result = self.client.packages(
            grouping_id=353991,
            business_profile_name=None,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/packages",
            params={
                "GroupingId": 353991,
            },
        )

    def test_vehicle_makes_maps_response(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [
                    {
                        "makeId": 1,
                        "makeDescription": "ACURA",
                    },
                    {
                        "makeId": 42,
                        "makeDescription": "VOLKSWAGEN",
                    },
                ],
            }
        )

        result = self.client.vehicle_makes(
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(
            result,
            (
                ChubbVehicleMake(
                    make_id=1,
                    name="ACURA",
                    description="ACURA",
                ),
                ChubbVehicleMake(
                    make_id=42,
                    name="VOLKSWAGEN",
                    description="VOLKSWAGEN",
                ),
            ),
        )


    def test_vehicle_makes_calls_expected_endpoint(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [],
            }
        )

        result = self.client.vehicle_makes(
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/makes",
            params={
                "BusinessProfileName": "BASE_TOM",
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_makes_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [],
            }
        )

        result = self.client.vehicle_makes(
            business_profile_name="  BASE_TOM  ",
            grouping_id="353991",
            rate_id="1472",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/makes",
            params={
                "BusinessProfileName": "BASE_TOM",
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_makes_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(ProviderInvalidResponseError):
            self.client.vehicle_makes(
                business_profile_name="   ",
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_makes_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(ProviderInvalidResponseError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=0,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_makes_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(ProviderInvalidResponseError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=-1,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_makes_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(ProviderInvalidResponseError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_makes_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(ProviderInvalidResponseError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_makes_rejects_non_mapping_payload(self):
        self.client._get_catalog = Mock(
            return_value=[],
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_makes_rejects_missing_makes_collection(self):
        self.client._get_catalog = Mock(
            return_value={},
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_makes_rejects_non_list_makes_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": {},
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_makes_rejects_non_mapping_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [
                    "ACURA",
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_makes_rejects_invalid_make_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [
                    {
                        "makeId": 0,
                        "makeDescription": "ACURA",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_makes_rejects_non_string_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [
                    {
                        "makeId": 1,
                        "makeDescription": None,
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_makes_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "makes": [
                    {
                        "makeId": 1,
                        "makeDescription": "   ",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_makes(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=1472,
            )

    def test_vehicle_submakes_maps_response(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [
                    {
                        "subMakeId": 1,
                        "subMakeDescription": "ACURA",
                    },
                    {
                        "subMakeId": 20,
                        "subMakeDescription": "INTEGRA",
                    },
                ],
            }
        )

        result = self.client.vehicle_submakes(
            business_profile_name="BASE_TOM",
            make_id=1,
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(
            result,
            (
                ChubbVehicleSubmake(
                    submake_id=1,
                    name="ACURA",
                    description="ACURA",
                ),
                ChubbVehicleSubmake(
                    submake_id=20,
                    name="INTEGRA",
                    description="INTEGRA",
                ),
            ),
        )


    def test_vehicle_submakes_calls_expected_endpoint(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [],
            }
        )

        result = self.client.vehicle_submakes(
            business_profile_name="BASE_TOM",
            make_id=1,
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/submakes",
            params={
                "BusinessProfileName": "BASE_TOM",
                "MakeId": 1,
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_submakes_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [],
            }
        )

        result = self.client.vehicle_submakes(
            business_profile_name="  BASE_TOM  ",
            make_id="1",
            grouping_id="353991",
            rate_id="1472",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/submakes",
            params={
                "BusinessProfileName": "BASE_TOM",
                "MakeId": 1,
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_submakes_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="   ",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_zero_make_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=0,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_negative_make_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=-1,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=0,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=-1,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_submakes_rejects_non_mapping_payload(self):
        self.client._get_catalog = Mock(
            return_value=[],
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_submakes_rejects_missing_collection(self):
        self.client._get_catalog = Mock(
            return_value={},
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_submakes_rejects_non_list_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": {},
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_submakes_rejects_non_mapping_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [
                    "ACURA",
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_submakes_rejects_invalid_submake_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [
                    {
                        "subMakeId": 0,
                        "subMakeDescription": "ACURA",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_submakes_rejects_non_string_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [
                    {
                        "subMakeId": 1,
                        "subMakeDescription": None,
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_submakes_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "submake": [
                    {
                        "subMakeId": 1,
                        "subMakeDescription": "   ",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_submakes(
                business_profile_name="BASE_TOM",
                make_id=1,
                grouping_id=353991,
                rate_id=1472,
            )

    def test_vehicle_types_maps_response(self):
        self.client._get_catalog = Mock(
            return_value={
                "types": [
                    {
                        "vehicleTypeId": 1,
                        "vehicleTypeDescription": "TL",
                    },
                    {
                        "vehicleTypeId": 550,
                        "vehicleTypeDescription": "ILX",
                    },
                ],
            }
        )

        result = self.client.vehicle_types(
            business_profile_name="BASE_TOM",
            submake_id=1,
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(
            result,
            (
                ChubbVehicleType(
                    vehicle_type_id=1,
                    name="TL",
                    description="TL",
                ),
                ChubbVehicleType(
                    vehicle_type_id=550,
                    name="ILX",
                    description="ILX",
                ),
            ),
        )


    def test_vehicle_types_calls_expected_endpoint(self):
        self.client._get_catalog = Mock(
            return_value={"types": []}
        )

        result = self.client.vehicle_types(
            business_profile_name="BASE_TOM",
            submake_id=1,
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/types",
            params={
                "BusinessProfileName": "BASE_TOM",
                "SubMakeId": 1,
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_types_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={"types": []}
        )

        self.client.vehicle_types(
            business_profile_name="  BASE_TOM  ",
            submake_id="1",
            grouping_id="353991",
            rate_id="1472",
        )

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/types",
            params={
                "BusinessProfileName": "BASE_TOM",
                "SubMakeId": 1,
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )

    def test_vehicle_types_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="   ",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_types_rejects_zero_submake_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=0,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_types_rejects_negative_submake_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=-1,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_types_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=0,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_types_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=-1,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_types_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_types_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=-1,
            )

        self.client._get_catalog.assert_not_called()

    def test_vehicle_types_rejects_non_mapping_payload(self):
        self.client._get_catalog = Mock(
            return_value=[],
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_types_rejects_missing_collection(self):
        self.client._get_catalog = Mock(
            return_value={},
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_types_rejects_non_list_collection(self):
        self.client._get_catalog = Mock(
            return_value={"types": {}}
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_types_rejects_non_mapping_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "types": ["TL"],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_types_rejects_invalid_vehicle_type_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "types": [
                    {
                        "vehicleTypeId": 0,
                        "vehicleTypeDescription": "TL",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_types_rejects_non_string_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "types": [
                    {
                        "vehicleTypeId": 1,
                        "vehicleTypeDescription": None,
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_types_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "types": [
                    {
                        "vehicleTypeId": 1,
                        "vehicleTypeDescription": "   ",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_types(
                business_profile_name="BASE_TOM",
                submake_id=1,
                grouping_id=353991,
                rate_id=1472,
            )

    def test_vehicle_years_maps_response(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [
                    {
                        "year": 2015,
                        "yearDescription": "2015",
                    },
                    {
                        "year": 2013,
                        "yearDescription": "2013",
                    },
                ],
            }
        )

        result = self.client.vehicle_years(
            business_profile_name="BASE_TOM",
            vehicle_type_id=1,
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(
            result,
            (
                ChubbVehicleYear(
                    year=2015,
                    name="2015",
                    description="2015",
                ),
                ChubbVehicleYear(
                    year=2013,
                    name="2013",
                    description="2013",
                ),
            ),
        )


    def test_vehicle_years_calls_expected_endpoint(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [],
            }
        )

        result = self.client.vehicle_years(
            business_profile_name="BASE_TOM",
            vehicle_type_id=1,
            grouping_id=353991,
            rate_id=1472,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/years",
            params={
                "BusinessProfileName": "BASE_TOM",
                "VehicleTypeId": 1,
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_years_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [],
            }
        )

        result = self.client.vehicle_years(
            business_profile_name="  BASE_TOM  ",
            vehicle_type_id="1",
            grouping_id="353991",
            rate_id="1472",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/years",
            params={
                "BusinessProfileName": "BASE_TOM",
                "VehicleTypeId": 1,
                "GroupingId": 353991,
                "RateId": 1472,
            },
        )


    def test_vehicle_years_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="   ",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_zero_vehicle_type_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=0,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_negative_vehicle_type_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=-1,
                grouping_id=353991,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=0,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=-1,
                rate_id=1472,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_years_rejects_non_mapping_payload(self):
        self.client._get_catalog = Mock(
            return_value=[],
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_years_rejects_missing_collection(self):
        self.client._get_catalog = Mock(
            return_value={},
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_years_rejects_non_list_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": {},
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_years_rejects_non_mapping_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [
                    2015,
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_years_rejects_invalid_year(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [
                    {
                        "year": 0,
                        "yearDescription": "2015",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_years_rejects_non_string_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [
                    {
                        "year": 2015,
                        "yearDescription": 2015,
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )


    def test_vehicle_years_rejects_empty_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "years": [
                    {
                        "year": 2015,
                        "yearDescription": "   ",
                    },
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_years(
                business_profile_name="BASE_TOM",
                vehicle_type_id=1,
                grouping_id=353991,
                rate_id=1472,
            )

    def _vehicle_data_item(self, **overrides):
        item = {
            "vehicleId": 1,
            "vehicleDescription": (
                "MDX SUV V6 IPC AUT 4 ABS CA CE PIEL CD CQ CB"
            ),
            "vehicleTypeId": 3,
            "trailerId": 1,
            "tonnageId": 7,
            "shortDescription": "MDX SUV AUT CA",
            "longDescription": (
                "MDX SUV V6 IPC AUT 4 ABS CA CE PIEL CD CQ CB"
            ),
            "tonnage": 0.0,
            "passengers": 7,
            "cmst": "010106003",
            "cmstConsecutive": 1,
            "active": True,
            "status": 1,
            "makeId": 1,
            "subMakeId": 1,
            "vehicleTypeDescription": "MDX",
            "trailerTypeDescription": "SIN REMOLQUE",
            "subMakeDescription": "ACURA",
            "makeDescription": "ACURA",
            "tonnageDescription": "Autos",
            "classId": 1,
            "vehicleGroupId": 1,
            "vehicleGroupDescription": "300 M",
            "statusDescription": "Activo",
            "mtc": "010301",
            "vehicleKey": "01010600301",
            "vehicleConditionId": 0,
        }

        item.update(overrides)

        return item

    def test_vehicle_data_maps_response(self):
        self.client._get_catalog = Mock(
            return_value={
                "messages": None,
                "vehicles": [
                    self._vehicle_data_item(),
                ],
            }
        )

        result = self.client.vehicle_data(
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=200,
            vehicle_year=2015,
        )

        self.assertEqual(
            result,
            (
                ChubbVehicleData(
                    vehicle_id=1,
                    description=(
                        "MDX SUV V6 IPC AUT 4 ABS CA CE "
                        "PIEL CD CQ CB"
                    ),
                    vehicle_type_id=3,
                    trailer_id=1,
                    tonnage_id=7,
                    short_description="MDX SUV AUT CA",
                    long_description=(
                        "MDX SUV V6 IPC AUT 4 ABS CA CE "
                        "PIEL CD CQ CB"
                    ),
                    tonnage=0.0,
                    passengers=7,
                    cmst="010106003",
                    cmst_consecutive=1,
                    active=True,
                    status=1,
                    make_id=1,
                    submake_id=1,
                    vehicle_type_description="MDX",
                    trailer_type_description="SIN REMOLQUE",
                    submake_description="ACURA",
                    make_description="ACURA",
                    tonnage_description="Autos",
                    class_id=1,
                    vehicle_group_id=1,
                    vehicle_group_description="300 M",
                    status_description="Activo",
                    mtc="010301",
                    vehicle_key="01010600301",
                    vehicle_condition_id=0,
                ),
            ),
        )


    def test_vehicle_data_calls_expected_endpoint(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [],
            }
        )

        result = self.client.vehicle_data(
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=200,
            vehicle_year=2015,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/data",
            params={
                "BusinessProfileName": "BASE_TOM",
                "GroupingId": 353991,
                "RateId": 200,
                "VehicleYear": 2015,
            },
        )


    def test_vehicle_data_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [],
            }
        )

        result = self.client.vehicle_data(
            business_profile_name="  BASE_TOM  ",
            grouping_id="353991",
            rate_id="200",
            vehicle_year="2015",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/data",
            params={
                "BusinessProfileName": "BASE_TOM",
                "GroupingId": 353991,
                "RateId": 200,
                "VehicleYear": 2015,
            },
        )


    def test_vehicle_data_rejects_empty_business_profile_name(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="   ",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_data_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=0,
                rate_id=200,
                vehicle_year=2015,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_data_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=-1,
                rate_id=200,
                vehicle_year=2015,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_data_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=0,
                vehicle_year=2015,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_data_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=-1,
                vehicle_year=2015,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_data_rejects_zero_vehicle_year(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_data_rejects_negative_vehicle_year(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=-1,
            )

        self.client._get_catalog.assert_not_called()

    def test_vehicle_data_rejects_non_mapping_payload(self):
        self.client._get_catalog = Mock(
            return_value=[],
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )


    def test_vehicle_data_rejects_missing_collection(self):
        self.client._get_catalog = Mock(
            return_value={},
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )


    def test_vehicle_data_rejects_non_list_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": {},
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )


    def test_vehicle_data_rejects_non_mapping_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    "invalid",
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )


    def test_vehicle_data_rejects_invalid_vehicle_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        vehicleId=0,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_rejects_non_string_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        vehicleDescription=123,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_rejects_empty_short_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        shortDescription="   ",
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )


    def test_vehicle_data_rejects_empty_long_description(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        longDescription="",
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_rejects_invalid_tonnage(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        tonnage=-1,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_rejects_invalid_passengers(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        passengers=-1,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_accepts_zero_passengers(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        passengers=0,
                    ),
                ],
            }
        )

        result = self.client.vehicle_data(
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=200,
            vehicle_year=2015,
        )

        self.assertEqual(result[0].passengers, 0)

    def test_vehicle_data_rejects_non_boolean_active(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        active=1,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_rejects_empty_vehicle_key(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        vehicleKey="   ",
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def test_vehicle_data_rejects_negative_vehicle_condition_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "vehicles": [
                    self._vehicle_data_item(
                        vehicleConditionId=-1,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_data(
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=200,
                vehicle_year=2015,
            )

    def _vehicle_use_item(self, **overrides):
            item = {
                "serviceId": 1,
                "serviceDescription": "PARTICULAR        ",
                "useId": 1,
                "useDescription": "PRIVADO",
            }
            item.update(overrides)
            return item

    def test_vehicle_uses_maps_response(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [
                    self._vehicle_use_item(),
                ],
            }
        )

        result = self.client.vehicle_uses(
            grouping_id=207637,
            country_subdivision_id=1,
            rate_id=400,
            use_id=1,
        )

        self.assertEqual(
            result,
            (
                ChubbVehicleUse(
                    service_id=1,
                    service_description="PARTICULAR",
                    use_id=1,
                    use_description="PRIVADO",
                ),
            ),
        )


    def test_vehicle_uses_calls_expected_endpoint(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [],
            }
        )

        result = self.client.vehicle_uses(
            grouping_id=207637,
            country_subdivision_id=1,
            rate_id=400,
            use_id=1,
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/uses",
            params={
                "GroupingId": 207637,
                "CountrySubdivisionId": 1,
                "RateId": 400,
                "UseId": 1,
            },
        )


    def test_vehicle_uses_normalizes_parameters(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [],
            }
        )

        result = self.client.vehicle_uses(
            grouping_id="207637",
            country_subdivision_id="1",
            rate_id="400",
            use_id="1",
        )

        self.assertEqual(result, ())

        self.client._get_catalog.assert_called_once_with(
            "/catalogs/vehicles/uses",
            params={
                "GroupingId": 207637,
                "CountrySubdivisionId": 1,
                "RateId": 400,
                "UseId": 1,
            },
        )


    def test_vehicle_uses_rejects_zero_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=0,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_negative_grouping_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=-1,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_zero_country_subdivision_id(
        self,
    ):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=0,
                rate_id=400,
                use_id=1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_negative_country_subdivision_id(
        self,
    ):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=-1,
                rate_id=400,
                use_id=1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_zero_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=0,
                use_id=1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_negative_rate_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=-1,
                use_id=1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_zero_use_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=0,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_negative_use_id(self):
        self.client._get_catalog = Mock()

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=-1,
            )

        self.client._get_catalog.assert_not_called()


    def test_vehicle_uses_rejects_non_mapping_payload(self):
        self.client._get_catalog = Mock(
            return_value=[],
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_missing_collection(self):
        self.client._get_catalog = Mock(
            return_value={},
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_non_list_collection(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": {},
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_non_mapping_item(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [
                    "PARTICULAR",
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_invalid_service_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [
                    self._vehicle_use_item(
                        serviceId=0,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_non_string_service_description(
        self,
    ):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [
                    self._vehicle_use_item(
                        serviceDescription=None,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_empty_service_description(
        self,
    ):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [
                    self._vehicle_use_item(
                        serviceDescription="   ",
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_invalid_response_use_id(self):
        self.client._get_catalog = Mock(
            return_value={
                "servicesUses": [
                    self._vehicle_use_item(
                        useId=0,
                    ),
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.client.vehicle_uses(
                grouping_id=207637,
                country_subdivision_id=1,
                rate_id=400,
                use_id=1,
            )


    def test_vehicle_uses_rejects_invalid_use_description(self):
        invalid_values = (
            None,
            "   ",
        )

        for invalid_value in invalid_values:
            with self.subTest(
                invalid_value=invalid_value,
            ):
                self.client._get_catalog = Mock(
                    return_value={
                        "servicesUses": [
                            self._vehicle_use_item(
                                useDescription=invalid_value,
                            ),
                        ],
                    }
                )

                with self.assertRaises(ValueError):
                    self.client.vehicle_uses(
                        grouping_id=207637,
                        country_subdivision_id=1,
                        rate_id=400,
                        use_id=1,
                    )

