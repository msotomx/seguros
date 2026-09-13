from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.persons.provider_resolver import (
    PersonProviderResolver,
)


class PersonProviderResolverTests(
    SimpleTestCase
):

    def test_build_resuelve_provider_registrado(
        self,
    ):
        provider = Mock()
        provider.provider_code = "CHUBB"

        builder = Mock()
        builder.build.return_value = provider

        resolver = PersonProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        result = resolver.build(
            provider_code="chubb",
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.assertIs(
            result,
            provider,
        )

        builder.build.assert_called_once_with(
            ambiente="SIT",
            ramo="AUTOS",
        )

    def test_build_rechaza_provider_no_registrado(
        self,
    ):
        builder = Mock()

        resolver = PersonProviderResolver(
            builders={
                "CHUBB": builder,
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            "No existe builder",
        ):
            resolver.build(
                provider_code="QUALITAS",
                ambiente="SIT",
                ramo="AUTOS",
            )

    def test_build_rechaza_provider_code_distinto(
        self,
    ):
        provider = Mock()
        provider.provider_code = "OTRO"

        builder = Mock()
        builder.build.return_value = provider

        resolver = PersonProviderResolver(
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
