from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.documents.contracts import (
    PolicyDocumentRequest,
    PolicyDocumentResult,
)
from integrations.providers.chubb.document_provider import (
    ChubbDocumentProvider,
)


class ChubbDocumentProviderTests(SimpleTestCase):
    def test_maps_request_and_delegates_to_client(self):
        mapper = Mock()
        client = Mock()

        internal_request = PolicyDocumentRequest(
            provider_policy_id="99007704",
            provider_policy_key="M6",
            risk_number=1,
        )

        chubb_request = Mock()
        expected = PolicyDocumentResult(
            provider_code="CHUBB",
            provider_policy_id="99007704",
            provider_policy_key="M6",
            documents=(),
        )

        mapper.map.return_value = chubb_request
        client.get_policy_documents.return_value = expected

        provider = ChubbDocumentProvider(
            client=client,
            request_mapper=mapper,
        )

        result = provider.get_policy_documents(
            internal_request
        )

        self.assertIs(result, expected)
        mapper.map.assert_called_once_with(
            internal_request
        )
        client.get_policy_documents.assert_called_once_with(
            chubb_request
        )
