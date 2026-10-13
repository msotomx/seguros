from django.test import SimpleTestCase

from integrations.providers.chubb.document_contracts import (
    ChubbPolicyDocumentRequest,
)
from integrations.providers.chubb.document_mappers import (
    ChubbPolicyDocumentRequestMapper,
    ChubbPolicyDocumentResponseMapper,
)

class ChubbPolicyDocumentRequestMapperTests(SimpleTestCase):
    def test_maps_policy_document_request_to_provider_payload(self):
        request = ChubbPolicyDocumentRequest(
            policy_key="M6",
            policy_id=99007704,
            risk_number=1,
            generate_all_receipts=True,
            copies=0,
        )

        payload = ChubbPolicyDocumentRequestMapper.to_payload(request)

        self.assertEqual(
            payload,
            {
                "policies": [
                    {
                        "policyKey": "M6",
                        "policyId": 99007704,
                        "riskNumber": 1,
                        "generateAllReceipts": True,
                        "copies": 0,
                    }
                ]
            },
        )

    def test_omits_risk_number_when_not_provided(self):
        request = ChubbPolicyDocumentRequest(
            policy_key="M6",
            policy_id=99007704,
            risk_number=None,
            generate_all_receipts=True,
            copies=0,
        )

        payload = ChubbPolicyDocumentRequestMapper.to_payload(request)

        policy = payload["policies"][0]

        self.assertNotIn("riskNumber", policy)

    def test_rejects_invalid_request_type(self):
        with self.assertRaisesRegex(
            TypeError,
            "request debe ser ChubbPolicyDocumentRequest",
        ):
            ChubbPolicyDocumentRequestMapper.to_payload(object())

class ChubbPolicyDocumentResponseMapperTests(SimpleTestCase):
    def setUp(self):
        self.request = ChubbPolicyDocumentRequest(
            policy_key="M6",
            policy_id=99007704,
            risk_number=1,
            generate_all_receipts=True,
            copies=0,
        )

    def test_maps_success_response_and_decodes_base64(self):
        response = {
            "policies": [
                {
                    "policyKey": "M6",
                    "policyId": 99007704,
                    "success": True,
                    "documents": [
                        {
                            "orderId": 123,
                            "fileName": "M699007704_00001.pdf",
                            "document": "JVBERi10ZXN0",
                        }
                    ],
                }
            ],
        }

        result = ChubbPolicyDocumentResponseMapper.to_internal(
            response=response,
            request=self.request,
        )

        self.assertEqual(result.provider_code, "CHUBB")
        self.assertEqual(
            result.provider_policy_id,
            "99007704",
        )
        self.assertEqual(
            result.provider_policy_key,
            "M6",
        )
        self.assertEqual(len(result.documents), 1)

        document = result.documents[0]

        self.assertEqual(document.order_id, "123")
        self.assertEqual(
            document.file_name,
            "M699007704_00001.pdf",
        )
        self.assertEqual(
            document.content,
            b"%PDF-test",
        )

    def test_rejects_unsuccessful_response(self):
        response = {
            "policies": [
                {
                    "policyKey": "M6",
                    "policyId": 99007704,
                    "success": False,
                    "documents": [],
                }
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            "Chubb no generó los documentos",
        ):
            ChubbPolicyDocumentResponseMapper.to_internal(
                response=response,
                request=self.request,
            )

    def test_rejects_success_response_without_documents(self):
        response = {
            "policies": [
                {
                    "policyKey": "M6",
                    "policyId": 99007704,
                    "success": True,
                    "documents": [],
                }
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            "Chubb respondió sin documentos",
        ):
            ChubbPolicyDocumentResponseMapper.to_internal(
                response=response,
                request=self.request,
            )

    def test_rejects_invalid_base64(self):
        response = {
            "policies": [
                {
                    "policyKey": "M6",
                    "policyId": 99007704,
                    "success": True,
                    "documents": [
                        {
                            "orderId": 123,
                            "fileName": "policy.pdf",
                            "document": "%%%INVALID%%%",
                        }
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            "Base64 inválido",
        ):
            ChubbPolicyDocumentResponseMapper.to_internal(
                response=response,
                request=self.request,
            )
