from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.providers.chubb.issue_provider_builder import (
    ChubbIssueProviderBuilder,
)


class ChubbIssueProviderBuilderTests(TestCase):

    def setUp(self):
        self.configuration_service = Mock()

        self.configuration = SimpleNamespace(
            id=25,
            supports_issue=True,
        )

        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.client_factory = Mock()
        self.mapper_factory = Mock()
        self.provider_factory = Mock()

        self.client = Mock()
        self.mapper = Mock()
        self.provider = Mock()

        self.client_factory.return_value = self.client
        self.mapper_factory.return_value = self.mapper
        self.provider_factory.return_value = self.provider

        self.builder = ChubbIssueProviderBuilder(
            configuration_service=(
                self.configuration_service
            ),
            client_factory=self.client_factory,
            mapper_factory=self.mapper_factory,
            provider_factory=self.provider_factory,
        )

    def test_build_constructs_issue_provider(self):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.mapper_factory.assert_called_once_with()

        self.client_factory.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            configuration=self.configuration,
        )

        self.provider_factory.assert_called_once_with(
            provider_id=25,
            client=self.client,
            request_mapper=self.mapper,
        )

        self.assertIs(
            result,
            self.provider,
        )

    def test_build_rejects_configuration_without_issue_support(self):
        self.configuration.supports_issue = False

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "operación de emisión",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.mapper_factory.assert_not_called()
        self.client_factory.assert_not_called()
        self.provider_factory.assert_not_called()

    def test_build_requires_positive_provider_id(self):
        self.configuration.id = 0

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "'id' debe ser un entero positivo",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        self.mapper_factory.assert_not_called()
        self.client_factory.assert_not_called()
        self.provider_factory.assert_not_called()

    def test_build_does_not_require_fiscal_settings(self):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.mapper_factory.assert_called_once_with()

        self.assertIs(
            result,
            self.provider,
        )

    def test_build_uses_explicit_configuration_without_get_active(
        self,
    ):
        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        self.configuration_service.get_active.assert_not_called()

        self.mapper_factory.assert_called_once_with()

        self.client_factory.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            configuration=self.configuration,
        )

        self.provider_factory.assert_called_once_with(
            provider_id=25,
            client=self.client,
            request_mapper=self.mapper,
        )

        self.assertIs(
            result,
            self.provider,
        )
