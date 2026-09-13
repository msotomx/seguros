from django.test import SimpleTestCase

from integrations.quotes.provider_resolver import (
    QuoteProviderResolver,
)
from integrations.quotes.provider_resolver_factory import (
    build_quote_provider_resolver,
)


class QuoteProviderResolverFactoryTests(
    SimpleTestCase
):

    def test_build_quote_provider_resolver(
        self,
    ):
        resolver = build_quote_provider_resolver()

        self.assertIsInstance(
            resolver,
            QuoteProviderResolver,
        )
