from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.providers.chubb.document_provider_builder import (
    ChubbDocumentProviderBuilder,
)


class ChubbDocumentProviderBuilderTests(SimpleTestCase):
    def setUp(self):
        self.configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            supports_documents=True,
            settings={
                "DOCUMENTS_BASE_URL": (
                    "https://documents.example.test"
                ),
                "DOCUMENTS_GENERATE_ALL_RECEIPTS": True,
                "DOCUMENTS_COPIES": 0,
            },
        )

        self.client_factory = Mock()
        self.mapper_factory = Mock()
        self.provider_factory = Mock()

        self.builder = ChubbDocumentProviderBuilder(
            client_factory=self.client_factory,
            mapper_factory=self.mapper_factory,
            provider_factory=self.provider_factory,
        )

    def test_builds_provider_from_configuration(self):
        mapper = Mock()
        client = Mock()
        provider = Mock()

        self.mapper_factory.return_value = mapper
        self.client_factory.return_value = client
        self.provider_factory.return_value = provider

        result = self.builder.build(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
        )

        self.assertIs(result, provider)

        self.mapper_factory.assert_called_once_with(
            generate_all_receipts=True,
            copies=0,
        )

        self.client_factory.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.builder._configuration_service
            ),
            configuration=self.configuration,
        )

        self.provider_factory.assert_called_once_with(
            client=client,
            request_mapper=mapper,
        )

    def test_rejects_when_documents_not_supported(self):
        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            supports_documents=False,
            settings=self.configuration.settings,
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "no tiene habilitada la operación de documentos",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
                configuration=configuration,
            )

    def test_requires_generate_all_receipts(self):
        settings = dict(self.configuration.settings)
        settings.pop("DOCUMENTS_GENERATE_ALL_RECEIPTS")

        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            supports_documents=True,
            settings=settings,
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "DOCUMENTS_GENERATE_ALL_RECEIPTS",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
                configuration=configuration,
            )

    def test_requires_copies(self):
        settings = dict(self.configuration.settings)
        settings.pop("DOCUMENTS_COPIES")

        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            supports_documents=True,
            settings=settings,
        )

        with self.assertRaisesRegex(
            InvalidProviderSetting,
            "DOCUMENTS_COPIES",
        ):
            self.builder.build(
                ambiente="SIT",
                ramo="AUTOS",
                configuration=configuration,
            )
    