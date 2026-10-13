from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.providers.chubb.document_client import (
    ChubbDocumentClient,
)
from integrations.providers.chubb.document_contracts import (
    ChubbPolicyDocumentRequest,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


class ChubbDocumentClientTests(SimpleTestCase):
    def setUp(self):
        self.configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            api_version="1",
            timeout=30,
            source_application_id=123,
            settings={
                "DOCUMENTS_BASE_URL": (
                    "https://documents.example.test"
                ),
            },
        )

        self.auth_client = Mock()
        self.auth_client.get_token.return_value = "TOKEN"

        self.http_client = Mock()

        self.client = ChubbDocumentClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=self.configuration,
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        self.request = ChubbPolicyDocumentRequest(
            policy_key="M6",
            policy_id=99007704,
            risk_number=1,
            generate_all_receipts=True,
            copies=0,
        )

    def test_posts_policy_document_request(self):
        response = Mock()
        response.data = {
            "policies": [
                {
                    "policyKey": "M6",
                    "policyId": 99007704,
                    "success": True,
                    "documents": [
                        {
                            "orderId": 10,
                            "fileName": "policy.pdf",
                            "document": "JVBERi10ZXN0",
                        },
                    ],
                }
            ],
        }

        self.http_client.post.return_value = response

        result = self.client.get_policy_documents(
            self.request
        )

        self.auth_client.get_token.assert_called_once_with()

        self.http_client.post.assert_called_once_with(
            "/documents/policy",
            token="TOKEN",
            payload={
                "policies": [
                    {
                        "policyKey": "M6",
                        "policyId": 99007704,
                        "riskNumber": 1,
                        "generateAllReceipts": True,
                        "copies": 0,
                    },
                ],
            },
            headers={
                "CB-SourceApplication": "123",
            },
        )

        self.assertEqual(
            result.provider_policy_id,
            "99007704",
        )
        self.assertEqual(
            result.documents[0].content,
            b"%PDF-test",
        )

    def test_rejects_invalid_request_type(self):
        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "request debe ser ChubbPolicyDocumentRequest",
        ):
            self.client.get_policy_documents(object())

    def test_requires_source_application_id(self):
        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            source_application_id=None,
            settings={
                "DOCUMENTS_BASE_URL": (
                    "https://documents.example.test"
                ),
            },
        )

        client = ChubbDocumentClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration=configuration,
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "source_application_id",
        ):
            client.get_policy_documents(
                self.request
            )

        self.http_client.post.assert_not_called()

    def test_requires_documents_base_url_when_building_http_client(self):
        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT",
            source_application_id=123,
            settings={},
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "DOCUMENTS_BASE_URL",
        ):
            ChubbDocumentClient(
                ambiente="SIT",
                ramo="AUTOS",
                configuration=configuration,
                auth_client=self.auth_client,
            )
