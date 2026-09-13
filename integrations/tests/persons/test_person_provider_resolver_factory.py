from django.test import SimpleTestCase

from integrations.persons.provider_resolver import (
    PersonProviderResolver,
)
from integrations.persons.provider_resolver_factory import (
    build_person_provider_resolver,
)


class PersonProviderResolverFactoryTests(
    SimpleTestCase
):

    def test_build_person_provider_resolver(
        self,
    ):
        resolver = build_person_provider_resolver()

        self.assertIsInstance(
            resolver,
            PersonProviderResolver,
        )
