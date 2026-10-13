from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from integrations.providers.chubb.issue_client import (
    ChubbIssueClient,
)
from integrations.providers.chubb.issue_contracts import (
    ChubbIssueInvoiceRequest,
    ChubbIssueItemDetailRequest,
    ChubbIssueItemRequest,
    ChubbIssuePersonRequest,
    ChubbIssueRequest,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


class ChubbIssueClientTests(TestCase):

    def setUp(self):
        self.configuration = SimpleNamespace(
            base_url=(
                "https://sit.example.com/"
                "digital.quote.partners"
            ),
            api_version=1,
            timeout=30,
            source_application_id="ERP-SEGUROS",
        )

        self.configuration_service = Mock()
        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.token = Mock()

        self.auth_client = Mock()
        self.auth_client.get_token.return_value = (
            self.token
        )

        self.http_client = Mock()

        self.request = ChubbIssueRequest(
            quote_id=144479063,
            payment_type_id=12,
            insured=ChubbIssuePersonRequest(
                tran_id=57482667,
                person_id=18683522,
                address_id=1410484013,
            ),
            items=(
                ChubbIssueItemRequest(
                    item=ChubbIssueItemDetailRequest(
                        number=1,
                        package_id=1,
                        no_serie="JH4KA3270KC007497",
                        plate="ABC123",
                        engine_number="ENGINE-001",
                        reference="Cotizacion",
                        owner_tran_id=54870559,
                        owner_id=18624569,
                        owner_address_id=1410427928,
                        beneficiary_tran_id=54870559,
                        beneficiary_id=18624569,
                    ),
                ),
            ),
            invoice=ChubbIssueInvoiceRequest(
                legal_personality_id=0,
                rfc="TECV920523B27",
                name="EMISION",
                postal_code="20126",
                tax_regime=4,
                use_cfdi_id=11,
                email="test@yopmail.com",
                email_payment="test@yopmail.com",
                comments="Facturacion",
                purchase_order="ORDENDECOMPRA MEN",
            ),
        )

    def _client(self):
        return ChubbIssueClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

    def _successful_response(self):
        return {
            "success": True,
            "messages": None,
            "responseData": [
                {
                    "quoteKey": "M6 ",
                    "quotePolicyId": 99007664,
                    "netPremiumAmount": 35247.21,
                    "bonificationAmount": 0.0,
                    "surchargeAmount": 0.0,
                    "discountAmount": 0.0,
                    "totalPremiumAmount": 41582.77,
                    "insuredId": 18683522,
                    "insuredAddressId": 1410484013,
                    "items": [
                        {
                            "item": {
                                "number": 1,
                                "netPremiumAmount": 35247.21,
                                "rightAmount": 600.0,
                                "discountAmount": 0.0,
                                "surchargeAmount": 0.0,
                                "ivaAmount": 5735.56,
                                "totalPremiumAmount": 41582.77,
                            }
                        }
                    ],
                }
            ],
        }

    def test_issue_posts_serialized_payload(self):
        self.http_client.post.return_value = (
            SimpleNamespace(
                data=self._successful_response()
            )
        )

        client = self._client()

        result = client.issue(
            self.request
        )

        self.assertEqual(
            result.quote_policy_id,
            99007664,
        )
        self.assertEqual(
            result.quote_key,
            "M6",
        )

        self.auth_client.get_token.assert_called_once_with()

        self.http_client.post.assert_called_once()

        call = self.http_client.post.call_args

        self.assertEqual(
            call.args[0],
            "/issue",
        )

        self.assertIs(
            call.kwargs["token"],
            self.token,
        )

        self.assertEqual(
            call.kwargs["headers"],
            {
                "CB-SourceApplication": "ERP-SEGUROS",
            },
        )

        payload = call.kwargs["payload"]

        self.assertEqual(
            payload["quoteId"],
            144479063,
        )
        self.assertEqual(
            payload["paymentTypeId"],
            12,
        )
        self.assertEqual(
            payload["insured"]["id"],
            18683522,
        )
        self.assertEqual(
            payload["items"][0]["item"]["noSerie"],
            "JH4KA3270KC007497",
        )

    def test_issue_gets_active_configuration(self):
        self.http_client.post.return_value = (
            SimpleNamespace(
                data=self._successful_response()
            )
        )

        client = self._client()

        client.issue(
            self.request
        )

        (
            self.configuration_service
            .get_active
            .assert_called_once_with(
                provider="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
            )
        )

    def test_issue_rejects_invalid_request_type(self):
        client = self._client()

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "ChubbIssueRequest",
        ):
            client.issue({})

        self.auth_client.get_token.assert_not_called()
        self.http_client.post.assert_not_called()

    def test_issue_wraps_response_mapper_error(self):
        self.http_client.post.return_value = (
            SimpleNamespace(
                data={
                    "success": False,
                    "messages": [
                        {
                            "message": (
                                "Inciso 1: "
                                "El número de serie ya existe."
                            ),
                            "messageCode": 0,
                            "messageType": 2,
                        }
                    ],
                    "responseData": None,
                }
            )
        )

        client = self._client()

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "número de serie",
        ):
            client.issue(
                self.request
            )

    def test_issue_requires_source_application_id(self):
        self.configuration.source_application_id = None

        client = self._client()

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "source_application_id",
        ):
            client.issue(
                self.request
            )

        self.auth_client.get_token.assert_not_called()
        self.http_client.post.assert_not_called()

    def test_uses_explicit_configuration_without_get_active(
        self,
    ):
        client = ChubbIssueClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            configuration=self.configuration,
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        self.assertIs(
            client.configuration,
            self.configuration,
        )

        self.configuration_service.get_active.assert_not_called()

    @patch(
        "integrations.providers.chubb.issue_client."
        "ChubbAuthClient"
    )
    def test_passes_explicit_configuration_to_auth_client(
        self,
        auth_client_class,
    ):
        self.configuration_service.reset_mock()

        ChubbIssueClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            configuration=self.configuration,
            http_client=self.http_client,
        )

        self.configuration_service.get_active.assert_not_called()

        auth_client_class.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            configuration=self.configuration,
        )
