from unittest import TestCase

from integrations.providers.chubb.issue_contracts import (
    ChubbIssueInvoiceRequest,
    ChubbIssueItemDetailRequest,
    ChubbIssueItemRequest,
    ChubbIssuePersonRequest,
    ChubbIssueRequest,
)
from integrations.providers.chubb.issue_mappers import (
    ChubbIssueRequestMapper,
)


class ChubbIssueRequestMapperTests(TestCase):

    def setUp(self):
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
                        plate="stder45ring",
                        engine_number="er45",
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

    def test_issue_serializes_exact_chubb_payload(self):
        payload = ChubbIssueRequestMapper.issue(
            self.request
        )

        self.assertEqual(
            payload,
            {
                "quoteId": 144479063,
                "paymentTypeId": 12,
                "insured": {
                    "tranId": 57482667,
                    "id": 18683522,
                    "addressId": 1410484013,
                },
                "items": [
                    {
                        "item": {
                            "number": 1,
                            "packageId": 1,
                            "noSerie": "JH4KA3270KC007497",
                            "plate": "stder45ring",
                            "engineNumber": "er45",
                            "reference": "Cotizacion",
                            "ownerTranId": 54870559,
                            "ownerId": 18624569,
                            "ownerAddressId": 1410427928,
                            "beneficiaryTranId": 54870559,
                            "beneficiaryId": 18624569,
                        }
                    }
                ],
                "invoice": {
                    "legalPersonalityId": 0,
                    "rfc": "TECV920523B27",
                    "name": "EMISION",
                    "postalCode": "20126",
                    "taxRegime": 4,
                    "useCFDId": 11,
                    "email": "test@yopmail.com",
                    "emailPayment": "test@yopmail.com",
                    "coments": "Facturacion",
                    "purchaseOrder": "ORDENDECOMPRA MEN",
                },
            },
        )

    def test_issue_rejects_invalid_quote_id(self):
        request = ChubbIssueRequest(
            quote_id=0,
            payment_type_id=self.request.payment_type_id,
            insured=self.request.insured,
            items=self.request.items,
            invoice=self.request.invoice,
        )

        with self.assertRaisesRegex(
            ValueError,
            "quote_id",
        ):
            ChubbIssueRequestMapper.issue(request)

    def test_issue_requires_at_least_one_item(self):
        request = ChubbIssueRequest(
            quote_id=self.request.quote_id,
            payment_type_id=self.request.payment_type_id,
            insured=self.request.insured,
            items=(),
            invoice=self.request.invoice,
        )

        with self.assertRaisesRegex(
            ValueError,
            "al menos un item",
        ):
            ChubbIssueRequestMapper.issue(request)

    def test_issue_allows_zero_legal_personality_id(self):
        payload = ChubbIssueRequestMapper.issue(
            self.request
        )

        self.assertEqual(
            payload["invoice"]["legalPersonalityId"],
            0,
        )

    def test_issue_can_omit_invoice(self):
        request = ChubbIssueRequest(
            quote_id=self.request.quote_id,
            payment_type_id=self.request.payment_type_id,
            insured=self.request.insured,
            items=self.request.items,
            invoice=None,
        )

        payload = ChubbIssueRequestMapper.issue(
            request
        )

        self.assertNotIn(
            "invoice",
            payload,
        )
