from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.documents.provider_resolver import (
    DocumentProviderResolver,
)


class DocumentProviderResolverTests(SimpleTestCase):
    def test_builds_requested_provider(self):
        builder = Mock()
        builder.provider_code = "CHUBB"

        provider = Mock()
        provider.provider_code = "CHUBB"
        builder.build.return_value = provider

        resolver = DocumentProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        configuration = Mock()

        result = resolver.build(
            provider_code=" chubb ",
            ambiente="SIT",
            ramo="AUTOS",
            configuration=configuration,
        )

        self.assertIs(result, provider)

        builder.build.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=configuration,
        )

    def test_rejects_unknown_provider(self):
        builder = Mock()
        builder.provider_code = "CHUBB"

        resolver = DocumentProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "No existe builder de documentos para provider=OTRO",
        ):
            resolver.build(
                provider_code="OTRO",
                ambiente="SIT",
                ramo="AUTOS",
            )

    def test_rejects_empty_builders(self):
        with self.assertRaisesRegex(
            ValueError,
            "Debe registrarse al menos un DocumentProviderBuilder",
        ):
            DocumentProviderResolver(
                builders={},
            )

    def test_rejects_provider_code_mismatch(self):
        builder = Mock()

        provider = Mock()
        provider.provider_code = "OTRO"
        builder.build.return_value = provider

        resolver = DocumentProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "código distinto al solicitado",
        ):
            resolver.build(
                provider_code="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
            )
