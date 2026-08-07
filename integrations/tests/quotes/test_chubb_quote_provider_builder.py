from unittest import TestCase
from unittest.mock import Mock

from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.providers.chubb.quote_provider_builder import (
    ChubbQuoteProviderBuilder,
)


def _configuration(
    **overrides,
) -> ProviderConfiguration:
    values = {
        "id": 1,
        "provider": "CHUBB",
        "ambiente": "SIT",
        "ramo": "AUTOS",
        "nombre": "Chubb SIT Autos",
        "base_url": "https://chubb.example.test",
        "api_version": "1",
        "timeout": 30,
        "business_profile_id": 7190,
        "grouping_id": 353991,
        "rate_id": 453,
        "source_application_id": 23,
        "supports_quote": True,
        "settings": {
            "PRODUCT_ID": 1,
            "AGENT_OPTION_ID": 91840,
            "CONDUIT_ID": 0,
            "CALCULATION_TYPE_ID": 2,
            "CURRENCY_ID": 1,
            "PAYMENT_TYPE_ID": 12,
            "INSURED_AMOUNT_TYPE_ID": 1,
            "DEDUCTIBLE_TYPE_ID": 1,
            "NADASC": False,
            "GENDER_IDS": {
                "M": 1,
                "F": 2,
            },
        },
    }

    values.update(overrides)

    return ProviderConfiguration(**values)


class ChubbQuoteProviderBuilderTests(TestCase):
    def setUp(self) -> None:
        self.configuration = _configuration()

        self.configuration_service = Mock()
        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.client = Mock()
        self.client_factory = Mock(
            return_value=self.client
        )

        self.request_mapper = Mock()
        self.mapper_factory = Mock(
            return_value=self.request_mapper
        )

        self.provider = Mock()
        self.provider_factory = Mock(
            return_value=self.provider
        )

        self.builder = ChubbQuoteProviderBuilder(
            configuration_service=(
                self.configuration_service
            ),
            client_factory=self.client_factory,
            mapper_factory=self.mapper_factory,
            provider_factory=self.provider_factory,
        )

    def test_build_loads_active_chubb_configuration(self):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.assertIs(result, self.provider)

        self.configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

    def test_build_constructs_mapper_from_configuration(self):
        self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.mapper_factory.assert_called_once_with(
            product_id=1,
            business_profile_id=7190,
            agent_id="91840",
            conduit_id=0,
            grouping_id=353991,
            rate_id=453,
            calculation_type_id=2,
            currency_id=1,
            payment_type_id=12,
            insured_amount_type_id=1,
            deductible_type_id=1,
            nadasc=False,
            gender_ids={
                "M": 1,
                "F": 2,
            },
        )

    def test_build_constructs_client(self):
        self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.client_factory.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
        )

    def test_build_constructs_provider(self):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.provider_factory.assert_called_once_with(
            client=self.client,
            request_mapper=self.request_mapper,
        )
        self.assertIs(result, self.provider)

    def test_build_rejects_disabled_quote_operation(self):
        self.configuration_service.get_active.return_value = (
            _configuration(
                supports_quote=False,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "no tiene habilitada",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.mapper_factory.assert_not_called()
        self.client_factory.assert_not_called()

    def test_build_rejects_missing_structural_field(self):
        self.configuration_service.get_active.return_value = (
            _configuration(
                business_profile_id=None,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "business_profile_id",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()

    def test_build_rejects_missing_required_setting(self):
        settings = dict(
            self.configuration.settings
        )
        settings.pop("PRODUCT_ID")

        self.configuration_service.get_active.return_value = (
            _configuration(
                settings=settings,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "PRODUCT_ID",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()

    def test_build_rejects_invalid_gender_ids(self):
        settings = dict(
            self.configuration.settings
        )
        settings["GENDER_IDS"] = []

        self.configuration_service.get_active.return_value = (
            _configuration(
                settings=settings,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "GENDER_IDS",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()

    def test_build_rejects_non_boolean_nadasc(self):
        settings = dict(
            self.configuration.settings
        )
        settings["NADASC"] = "false"

        self.configuration_service.get_active.return_value = (
            _configuration(
                settings=settings,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "NADASC",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()
