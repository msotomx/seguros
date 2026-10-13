from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.documents.contracts import (
    PolicyDocument,
    PolicyDocumentRequest,
    PolicyDocumentResult,
)
from integrations.documents.service import DocumentService


class DocumentServiceTests(SimpleTestCase):
    def setUp(self):
        self.request = PolicyDocumentRequest(
            provider_policy_id="POL-123",
            provider_policy_key="PK",
            risk_number=1,
        )

    def test_get_policy_documents_delegates_to_provider(self):
        provider = Mock()
        provider.provider_code = "TEST"

        expected = PolicyDocumentResult(
            provider_code="TEST",
            provider_policy_id="POL-123",
            provider_policy_key="PK",
            documents=(
                PolicyDocument(
                    order_id="1",
                    file_name="policy.pdf",
                    content=b"%PDF-test",
                ),
            ),
        )

        provider.get_policy_documents.return_value = expected

        service = DocumentService([provider])

        result = service.get_policy_documents(
            "test",
            self.request,
        )

        self.assertIs(result, expected)
        provider.get_policy_documents.assert_called_once_with(
            self.request
        )

    def test_rejects_duplicate_provider_codes(self):
        provider_a = Mock()
        provider_a.provider_code = "TEST"

        provider_b = Mock()
        provider_b.provider_code = "test"

        with self.assertRaisesRegex(
            ValueError,
            "DocumentProvider duplicado: TEST",
        ):
            DocumentService(
                [provider_a, provider_b]
            )

    def test_raises_when_provider_does_not_exist(self):
        service = DocumentService([])

        with self.assertRaisesRegex(
            ValueError,
            "No existe DocumentProvider para TEST",
        ):
            service.get_policy_documents(
                "test",
                self.request,
            )
