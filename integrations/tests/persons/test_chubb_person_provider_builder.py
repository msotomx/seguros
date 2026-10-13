from unittest import TestCase
from unittest.mock import Mock

from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.providers.chubb.person_provider_builder import (
    ChubbPersonProviderBuilder,
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
        "base_url": "https://quote.example.test",
        "api_version": "1",
        "timeout": 30,
        "source_application_id": 23,
        "supports_issue": True,
        "settings": {
            "PERSON_BASE_URL": (
                "https://person.example.test"
            ),
            "PERSON_TYPE_ID": None,
            "LEGAL_PERSONALITY_ID": 0,
            "MARITAL_STATUS_ID": 1,
            "ADDRESS_TYPE_ID": 1,
            "GENDER_IDS": {
                "MASCULINO": 1,
                "FEMENINO": 2,
            },
        },
    }

    values.update(overrides)

    return ProviderConfiguration(**values)


class ChubbPersonProviderBuilderTests(TestCase):

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

        self.catalog_client = Mock()
        self.catalog_client_factory = Mock(
            return_value=self.catalog_client
        )

        self.request_mapper = Mock()
        self.mapper_factory = Mock(
            return_value=self.request_mapper
        )

        self.provider = Mock()
        self.provider_factory = Mock(
            return_value=self.provider
        )

        self.builder = ChubbPersonProviderBuilder(
            configuration_service=(
                self.configuration_service
            ),
            client_factory=self.client_factory,
            catalog_client_factory=self.catalog_client_factory,
            mapper_factory=self.mapper_factory,
            provider_factory=self.provider_factory,
        )

    def test_build_constructs_catalog_client_with_exact_configuration(
        self,
    ):
        self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        self.catalog_client_factory.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            configuration=self.configuration,
        )

    def test_build_loads_active_chubb_configuration(
        self,
    ):
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

    def test_build_constructs_mapper_from_configuration(
        self,
    ):
        self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.mapper_factory.assert_called_once_with(
            person_type_id=None,
            legal_personality_id=0,
            marital_status_id=1,
            address_type_id=1,
            gender_ids={
                "MASCULINO": 1,
                "FEMENINO": 2,
            },
        )

    def test_build_constructs_client(
        self,
    ):
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
            configuration=self.configuration,
        )

    def test_build_constructs_provider_with_configuration_id(
        self,
    ):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )
        self.provider_factory.assert_called_once_with(
            provider_id=1,
            client=self.client,
            request_mapper=self.request_mapper,
            catalog_client=self.catalog_client,
        )

        self.assertIs(result, self.provider)

    def test_build_accepts_null_person_type_id(
        self,
    ):
        self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.mapper_factory.assert_called_once()

    def test_build_rejects_missing_person_type_id(
        self,
    ):
        settings = dict(
            self.configuration.settings
        )
        settings.pop("PERSON_TYPE_ID")

        self.configuration_service.get_active.return_value = (
            _configuration(
                settings=settings,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "PERSON_TYPE_ID",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()

    def test_build_accepts_zero_legal_personality_id(
        self,
    ):
        self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.mapper_factory.assert_called_once()

    def test_build_rejects_negative_legal_personality_id(
        self,
    ):
        settings = dict(
            self.configuration.settings
        )
        settings["LEGAL_PERSONALITY_ID"] = -1

        self.configuration_service.get_active.return_value = (
            _configuration(
                settings=settings,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "LEGAL_PERSONALITY_ID",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()

    def test_build_rejects_missing_person_base_url(
        self,
    ):
        settings = dict(
            self.configuration.settings
        )
        settings.pop("PERSON_BASE_URL")

        self.configuration_service.get_active.return_value = (
            _configuration(
                settings=settings,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "PERSON_BASE_URL",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.client_factory.assert_not_called()

    def test_build_rejects_invalid_gender_ids(
        self,
    ):
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

    def test_build_rejects_disabled_issue_operation(
        self,
    ):
        self.configuration_service.get_active.return_value = (
            _configuration(
                supports_issue=False,
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

    def test_build_rejects_invalid_provider_id(
        self,
    ):
        self.configuration_service.get_active.return_value = (
            _configuration(
                id=0,
            )
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "'id' debe ser mayor que cero",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.mapper_factory.assert_not_called()
        self.client_factory.assert_not_called()

    def test_build_uses_explicit_configuration_without_get_active(
        self,
    ):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        self.configuration_service.get_active.assert_not_called()

        self.client_factory.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            configuration=self.configuration,
        )

        self.provider_factory.assert_called_once_with(
            provider_id=1,
            client=self.client,
            request_mapper=self.request_mapper,
            catalog_client=self.catalog_client,
        )

        self.assertIs(
            result,
            self.provider,
        )
