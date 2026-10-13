from django.test import SimpleTestCase

from integrations.documents.provider_resolver import (
    DocumentProviderResolver,
)
from integrations.documents.provider_resolver_factory import (
    build_document_provider_resolver,
)


class DocumentProviderResolverFactoryTests(SimpleTestCase):
    def test_builds_document_provider_resolver(self):
        resolver = build_document_provider_resolver()

        self.assertIsInstance(
            resolver,
            DocumentProviderResolver,
        )
        