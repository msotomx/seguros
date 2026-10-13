from django.test import SimpleTestCase

from integrations.providers.chubb.document_contracts import (
    ChubbPolicyDocumentItem,
    ChubbPolicyDocumentRequest,
    ChubbPolicyDocumentResult,
)


class ChubbPolicyDocumentContractsTests(SimpleTestCase):
    def test_keeps_provider_document_contract(self):
        request = ChubbPolicyDocumentRequest(
            policy_key="PK",
            policy_id=123,
            risk_number=1,
            generate_all_receipts=True,
            copies=0,
        )

        document = ChubbPolicyDocumentItem(
            order_id="456",
            file_name="policy.pdf",
            document="JVBERi0xLjQ=",
        )

        result = ChubbPolicyDocumentResult(
            success=True,
            documents=(document,),
        )

        self.assertEqual(request.policy_key, "PK")
        self.assertEqual(request.policy_id, 123)
        self.assertEqual(request.risk_number, 1)
        self.assertTrue(request.generate_all_receipts)
        self.assertEqual(request.copies, 0)

        self.assertTrue(result.success)
        self.assertEqual(result.documents[0].order_id, "456")
        self.assertEqual(result.documents[0].file_name, "policy.pdf")
        self.assertEqual(
            result.documents[0].document,
            "JVBERi0xLjQ=",
        )
