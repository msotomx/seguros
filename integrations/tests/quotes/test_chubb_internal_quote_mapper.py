from datetime import date
from decimal import Decimal
from unittest import TestCase

from integrations.providers.chubb.internal_quote_mapper import (
    ChubbInternalQuoteRequestMapper,
)
from integrations.quotes.contracts import (
    InternalQuoteRequest,
    QuoteCoverageRequest,
    QuoteDiscountRequest,
    QuoteDriver,
    QuotePackageRequest,
    QuoteRisk,
    QuoteVehicle,
)


class ChubbInternalQuoteRequestMapperTests(TestCase):
    def setUp(self):
        self.mapper = ChubbInternalQuoteRequestMapper(
            product_id=91,
            business_profile_id=92,
            agent_id="AGENT-93",
            conduit_id=94,
            grouping_id=95,
            rate_id=96,
            calculation_type_id=97,
            currency_id=98,
            payment_type_id=99,
            insured_amount_type_id=101,
            deductible_type_id=102,
            nadasc=True,
            gender_ids={
                "M": 103,
                "F": 104,
            },
        )

        self.request = InternalQuoteRequest(
            effective_date=date(2026, 8, 4),
            expiration_date=date(2027, 8, 4),
            prospect_name="Miguel Soto",
            reference="COT-0001",
            risks=(
                QuoteRisk(
                    reference="RISK-001",
                    vehicle=QuoteVehicle(
                        year=2025,
                        vehicle_key="VEHICLE-001",
                        use_code="105",
                        garage=True,
                        state_code="106",
                        municipality_code="107",
                        plate="ABC123",
                    ),
                    driver=QuoteDriver(
                        age=40,
                        gender="M",
                    ),
                    packages=(
                        QuotePackageRequest(
                            code="108",
                            selected=True,
                            coverages=(
                                QuoteCoverageRequest(
                                    code="109",
                                    insured_amount=Decimal(
                                        "250000.00"
                                    ),
                                    deductible=Decimal("5.00"),
                                ),
                            ),
                        ),
                    ),
                    discounts=(
                        QuoteDiscountRequest(
                            code="110",
                            percentage=Decimal("10.00"),
                        ),
                    ),
                ),
            ),
        )

    def test_create_quote_uses_configured_provider_values(self):
        result = self.mapper.create_quote(
            self.request
        )

        self.assertEqual(result.product_id, 91)
        self.assertEqual(
            result.business_profile_id,
            92,
        )
        self.assertEqual(result.agent_id, "AGENT-93")
        self.assertEqual(result.conduit_id, 94)
        self.assertEqual(result.grouping_id, 95)
        self.assertEqual(result.rate_id, 96)
        self.assertEqual(
            result.calculation_type_id,
            97,
        )
        self.assertEqual(result.currency_id, 98)
        self.assertEqual(
            result.payment_types[0].payment_type_id,
            99,
        )

        vehicle = result.items[0].vehicle

        self.assertEqual(
            vehicle.insured_amount_type_id,
            101,
        )
        self.assertEqual(
            vehicle.deductible_type_id,
            102,
        )
        self.assertTrue(vehicle.nadasc)
        self.assertEqual(vehicle.gender_id, 103)

        coverage = (
            result.items[0]
            .packages[0]
            .coverages[0]
        )

        self.assertEqual(
            coverage.deductible_type_id,
            102,
        )

    def test_create_quote_rejects_unconfigured_gender(self):
        request = InternalQuoteRequest(
            effective_date=self.request.effective_date,
            expiration_date=self.request.expiration_date,
            prospect_name=self.request.prospect_name,
            reference=self.request.reference,
            risks=(
                QuoteRisk(
                    reference="RISK-001",
                    vehicle=self.request.risks[0].vehicle,
                    driver=QuoteDriver(
                        age=40,
                        gender="X",
                    ),
                    packages=self.request.risks[0].packages,
                    discounts=self.request.risks[0].discounts,
                ),
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "Género no configurado",
        ):
            self.mapper.create_quote(request)
