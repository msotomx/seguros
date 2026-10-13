from unittest import TestCase

from integrations.issues.contracts import (
    InternalIssueRequest,
    IssueInvoice,
    IssuePartyReference,
    IssueRisk,
)
from integrations.providers.chubb.internal_issue_mapper import (
    ChubbInternalIssueRequestMapper,
)


class ChubbInternalIssueRequestMapperTests(TestCase):

    def setUp(self):
        self.mapper = ChubbInternalIssueRequestMapper(
            legal_personality_ids={
                "FISICA": 21,
            },
            tax_regime_ids={
                "SUELDOS": 22,
            },
            cfdi_use_ids={
                "SIN_EFECTOS": 23,
            },
        )

        insured = IssuePartyReference(
            provider_tran_id="1001",
            provider_person_id="1002",
            provider_address_id="1003",
        )

        owner = IssuePartyReference(
            provider_tran_id="2001",
            provider_person_id="2002",
            provider_address_id="2003",
        )

        beneficiary = IssuePartyReference(
            provider_tran_id="3001",
            provider_person_id="3002",
            provider_address_id=None,
        )

        self.request = InternalIssueRequest(
            provider_quote_id="4001",
            provider_quote_version_id="4002",
            payment_method_code="CONTADO",
            insured=insured,
            risks=(
                IssueRisk(
                    risk_number=1,
                    provider_package_id="5001",
                    vin="JH4KA3270KC007497",
                    plate="ABC123",
                    engine_number="ENGINE-001",
                    reference="COT-0001",
                    owner=owner,
                    beneficiary=beneficiary,
                ),
            ),
            invoice=IssueInvoice(
                tax_id="TECV920523B27",
                name="MIGUEL SOTO",
                postal_code="20126",
                legal_personality_code="FISICA",
                tax_regime_code="SUELDOS",
                cfdi_use_code="SIN_EFECTOS",
                email="miguel@example.com",
                payment_email="pagos@example.com",
                comments="Facturación",
                purchase_order="OC-001",
            ),
        )

    def test_issue_maps_internal_request_to_chubb_contract(self):
        result = self.mapper.issue(
            self.request,
            payment_type_id=12,
        )

        self.assertEqual(
            result.quote_id,
            4001,
        )
        self.assertEqual(
            result.payment_type_id,
            12,
        )

        self.assertEqual(
            result.insured.tran_id,
            1001,
        )
        self.assertEqual(
            result.insured.person_id,
            1002,
        )
        self.assertEqual(
            result.insured.address_id,
            1003,
        )

        item = result.items[0].item

        self.assertEqual(
            item.number,
            1,
        )
        self.assertEqual(
            item.package_id,
            5001,
        )
        self.assertEqual(
            item.no_serie,
            "JH4KA3270KC007497",
        )
        self.assertEqual(
            item.plate,
            "ABC123",
        )
        self.assertEqual(
            item.engine_number,
            "ENGINE-001",
        )
        self.assertEqual(
            item.reference,
            "COT-0001",
        )

        self.assertEqual(
            item.owner_tran_id,
            2001,
        )
        self.assertEqual(
            item.owner_id,
            2002,
        )
        self.assertEqual(
            item.owner_address_id,
            2003,
        )

        self.assertEqual(
            item.beneficiary_tran_id,
            3001,
        )
        self.assertEqual(
            item.beneficiary_id,
            3002,
        )

        invoice = result.invoice

        self.assertEqual(
            invoice.legal_personality_id,
            21,
        )
        self.assertEqual(
            invoice.tax_regime,
            22,
        )
        self.assertEqual(
            invoice.use_cfdi_id,
            23,
        )
        self.assertEqual(
            invoice.email_payment,
            "pagos@example.com",
        )

    def test_issue_normalizes_internal_mapping_codes(self):
        request = InternalIssueRequest(
            provider_quote_id=self.request.provider_quote_id,
            provider_quote_version_id=(
                self.request.provider_quote_version_id
            ),
            payment_method_code="  contado  ",
            insured=self.request.insured,
            risks=self.request.risks,
            invoice=self.request.invoice,
        )

        result = self.mapper.issue(
            request,
            payment_type_id=12,
        )

        self.assertEqual(
            result.payment_type_id,
            12,
        )

    def test_issue_rejects_invalid_payment_type_id(self):
        with self.assertRaisesRegex(
            ValueError,
            "payment_type_id",
        ):
            self.mapper.issue(
                self.request,
                payment_type_id=0,
            )

    def test_issue_rejects_invalid_provider_person_id(self):
        request = InternalIssueRequest(
            provider_quote_id=self.request.provider_quote_id,
            provider_quote_version_id=(
                self.request.provider_quote_version_id
            ),
            payment_method_code=self.request.payment_method_code,
            insured=IssuePartyReference(
                provider_tran_id="1001",
                provider_person_id="0",
                provider_address_id="1003",
            ),
            risks=self.request.risks,
            invoice=self.request.invoice,
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_person_id",
        ):
            self.mapper.issue(
                request,
                payment_type_id=12,
            )

    def test_issue_requires_owner(self):
        risk = self.request.risks[0]

        request = InternalIssueRequest(
            provider_quote_id=self.request.provider_quote_id,
            provider_quote_version_id=(
                self.request.provider_quote_version_id
            ),
            payment_method_code=self.request.payment_method_code,
            insured=self.request.insured,
            risks=(
                IssueRisk(
                    risk_number=risk.risk_number,
                    provider_package_id=(
                        risk.provider_package_id
                    ),
                    vin=risk.vin,
                    plate=risk.plate,
                    engine_number=risk.engine_number,
                    reference=risk.reference,
                    owner=None,
                    beneficiary=risk.beneficiary,
                ),
            ),
            invoice=self.request.invoice,
        )

        with self.assertRaisesRegex(
            ValueError,
            "requiere propietario",
        ):
            self.mapper.issue(
                request,
                payment_type_id=12,
            )

    def test_issue_requires_beneficiary(self):
        risk = self.request.risks[0]

        request = InternalIssueRequest(
            provider_quote_id=self.request.provider_quote_id,
            provider_quote_version_id=(
                self.request.provider_quote_version_id
            ),
            payment_method_code=self.request.payment_method_code,
            insured=self.request.insured,
            risks=(
                IssueRisk(
                    risk_number=risk.risk_number,
                    provider_package_id=(
                        risk.provider_package_id
                    ),
                    vin=risk.vin,
                    plate=risk.plate,
                    engine_number=risk.engine_number,
                    reference=risk.reference,
                    owner=risk.owner,
                    beneficiary=None,
                ),
            ),
            invoice=self.request.invoice,
        )

        with self.assertRaisesRegex(
            ValueError,
            "requiere beneficiario",
        ):
            self.mapper.issue(
                request,
                payment_type_id=12,
            )

    def test_issue_accepts_zero_legal_personality_id(self):
        mapper = ChubbInternalIssueRequestMapper(
            legal_personality_ids={
                "FISICA": 0,
            },
            tax_regime_ids={
                "SUELDOS": 22,
            },
            cfdi_use_ids={
                "SIN_EFECTOS": 23,
            },
        )

        result = mapper.issue(
            self.request,
            payment_type_id=12,
        )

        self.assertIsNotNone(
            result.invoice
        )
        self.assertEqual(
            result.invoice.legal_personality_id,
            0,
        )

    def test_issue_without_invoice_does_not_require_fiscal_mappings(
        self,
    ):
        mapper = ChubbInternalIssueRequestMapper()

        request = InternalIssueRequest(
            provider_quote_id=(
                self.request.provider_quote_id
            ),
            provider_quote_version_id=(
                self.request.provider_quote_version_id
            ),
            payment_method_code=(
                self.request.payment_method_code
            ),
            insured=self.request.insured,
            risks=self.request.risks,
            invoice=None,
        )

        result = mapper.issue(
            request,
            payment_type_id=12,
        )

        self.assertIsNone(
            result.invoice
        )
