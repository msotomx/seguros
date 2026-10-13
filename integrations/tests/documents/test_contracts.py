from django.test import SimpleTestCase

from integrations.documents.contracts import (
    PolicyDocument,
    PolicyDocumentRequest,
    PolicyDocumentResult,
)


class PolicyDocumentContractsTests(SimpleTestCase):
    def test_policy_document_result_keeps_binary_content(self):
        request = PolicyDocumentRequest(
            provider_policy_id="POL-123",
            provider_policy_key="PK",
            risk_number=1,
        )

        document = PolicyDocument(
            order_id="1",
            file_name="policy.pdf",
            content=b"%PDF-test",
        )

        result = PolicyDocumentResult(
            provider_code="TEST",
            provider_policy_id=request.provider_policy_id,
            provider_policy_key=request.provider_policy_key,
            documents=(document,),
            raw_response={"success": True},
        )

        self.assertEqual(result.provider_code, "TEST")
        self.assertEqual(result.provider_policy_id, "POL-123")
        self.assertEqual(result.provider_policy_key, "PK")
        self.assertEqual(result.documents[0].file_name, "policy.pdf")
        self.assertEqual(result.documents[0].content, b"%PDF-test")
