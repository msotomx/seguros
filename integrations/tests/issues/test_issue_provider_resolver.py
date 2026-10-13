from unittest import TestCase
from unittest.mock import Mock

from integrations.issues.provider_resolver import (
    IssueProviderResolver,
)


class IssueProviderResolverTests(TestCase):

    def test_build_returns_provider_from_registered_builder(self):
        builder = Mock()
        provider = Mock()
        provider.provider_code = "CHUBB"

        builder.build.return_value = provider

        resolver = IssueProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        result = resolver.build(
            provider_code="chubb",
            ambiente="SIT",
            ramo="AUTOS",
        )

        builder.build.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=None,
        )

        self.assertIs(
            result,
            provider,
        )

    def test_normalizes_builder_provider_code(self):
        builder = Mock()
        provider = Mock()
        provider.provider_code = "CHUBB"

        builder.build.return_value = provider

        resolver = IssueProviderResolver(
            builders={
                " chubb ": builder,
            },
        )

        result = resolver.build(
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.assertIs(
            result,
            provider,
        )

    def test_rejects_unknown_provider(self):
        builder = Mock()

        resolver = IssueProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "No existe builder de emisión para provider=AXA",
        ):
            resolver.build(
                provider_code="AXA",
                ambiente="SIT",
                ramo="AUTOS",
            )

        builder.build.assert_not_called()

    def test_rejects_provider_with_different_code(self):
        builder = Mock()
        provider = Mock()
        provider.provider_code = "AXA"

        builder.build.return_value = provider

        resolver = IssueProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "código distinto",
        ):
            resolver.build(
                provider_code="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
            )

    def test_requires_at_least_one_builder(self):
        with self.assertRaisesRegex(
            ValueError,
            "al menos un IssueProviderBuilder",
        ):
            IssueProviderResolver(
                builders={},
            )

    def test_rejects_non_string_provider_code(self):
        builder = Mock()

        resolver = IssueProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            TypeError,
            "provider_code debe ser una cadena",
        ):
            resolver.build(
                provider_code=123,
                ambiente="SIT",
                ramo="AUTOS",
            )

    def test_rejects_empty_provider_code(self):
        builder = Mock()

        resolver = IssueProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_code no puede estar vacío",
        ):
            resolver.build(
                provider_code="   ",
                ambiente="SIT",
                ramo="AUTOS",
            )

    def test_build_propagates_explicit_configuration(
        self,
    ):
        configuration = Mock()

        builder = Mock()

        provider = Mock()
        provider.provider_code = "CHUBB"

        builder.build.return_value = provider

        resolver = IssueProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        result = resolver.build(
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration=configuration,
        )

        builder.build.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=configuration,
        )

        self.assertIs(
            result,
            provider,
        )
