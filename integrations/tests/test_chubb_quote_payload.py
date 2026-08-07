from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from integrations.providers.chubb.contracts import (
    ChubbQuoteContext,
)
from integrations.providers.chubb.payloads import (
    ChubbQuotePayloadBuilder,
)
from integrations.providers.contracts import (
    QuoteInsured,
    QuoteRequest,
    QuoteVehicle,
)
from integrations.providers.exceptions import (
    ProviderQuoteError,
)


class ChubbQuotePayloadBuilderTest(SimpleTestCase):
    def setUp(self):
        self.request = QuoteRequest(
            provider_id=1,
            vehicle=QuoteVehicle(
                year=2024,
                brand_code="NISSAN",
                model_code="VERSA",
                version_code="ADVANCE",
                use_code="PARTICULAR",
                postal_code="31000",
                serial_number="3N1CN7AD0RL000001",
                plates="ABC123",
            ),
            insured=QuoteInsured(
                person_type="INDIVIDUAL",
                first_name="Miguel",
                last_name="Soto",
                birth_date=date(1980, 8, 20),
                gender_code="MALE",
            ),
            start_date=date(2026, 7, 11),
            end_date=date(2027, 7, 11),
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
        )

        self.context = ChubbQuoteContext(
            product_id=1,
            business_profile_id=7190,
            agent_id=93300,
            conduit_id=0,
            grouping_id=353796,
            rate_id=453,
            calculation_type_id=2,
            currency_id=1,
            payment_type_id=12,
            vehicle_key="01140300301",
            vehicle_id=1146,
            insured_amount_type_id=1,
            deductible_type_id=1,
            country_subdivision_id=1,
            municipality_id=42,
            vehicle_use_id=1,
            package_id=1,
            discount_percentage=Decimal("10"),
            bonus_percentage=Decimal("0"),
        )

    def test_builds_chubb_quote_payload(self):
        payload = ChubbQuotePayloadBuilder.build(
            request=self.request,
            context=self.context,
        )

        self.assertEqual(payload["quoteId"], 0)
        self.assertEqual(payload["quoteType"], 0)
        self.assertEqual(payload["productId"], 1)
        self.assertEqual(
            payload["businessprofileId"],
            7190,
        )
        self.assertEqual(
            payload["effectiveDate"],
            "2026-07-11",
        )
        self.assertEqual(
            payload["expirationDate"],
            "2027-07-11",
        )

        self.assertEqual(
            payload["paymentTypes"],
            [{"paymentTypeId": 12}],
        )

    def test_builds_vehicle(self):
        payload = ChubbQuotePayloadBuilder.build(
            request=self.request,
            context=self.context,
        )

        vehicle = payload["items"][0]["vehicle"]

        self.assertEqual(
            vehicle["vehicleKey"],
            "01140300301",
        )
        self.assertEqual(vehicle["vehicleId"], 1146)
        self.assertEqual(vehicle["year"], 2024)
        self.assertEqual(vehicle["useId"], 1)
        self.assertEqual(vehicle["zipCode"], 31000)
        self.assertEqual(
            vehicle["vin"],
            "3N1CN7AD0RL000001",
        )
        self.assertEqual(vehicle["plate"], "ABC123")
        self.assertEqual(vehicle["age"], 45)

    def test_builds_selected_package(self):
        payload = ChubbQuotePayloadBuilder.build(
            request=self.request,
            context=self.context,
        )

        packages = payload["items"][0]["packages"]

        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["packageId"], 1)
        self.assertTrue(packages[0]["selected"])
        self.assertEqual(packages[0]["coverages"], [])

    def test_builds_quote_headers(self):
        headers = ChubbQuotePayloadBuilder.build_headers(
            context=self.context,
        )

        self.assertEqual(
            headers,
            {
                "CB-SourceApplication": "23",
            },
        )

    def test_rejects_invalid_date_range(self):
        invalid_request = QuoteRequest(
            provider_id=self.request.provider_id,
            vehicle=self.request.vehicle,
            insured=self.request.insured,
            start_date=date(2026, 7, 11),
            end_date=date(2026, 7, 11),
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
        )

        with self.assertRaises(ProviderQuoteError):
            ChubbQuotePayloadBuilder.build(
                request=invalid_request,
                context=self.context,
            )

    def test_rejects_invalid_context_id(self):
        invalid_context = ChubbQuoteContext(
            product_id=0,
            business_profile_id=7190,
            agent_id=93300,
            conduit_id=0,
            grouping_id=353796,
            rate_id=453,
            calculation_type_id=2,
            currency_id=1,
            payment_type_id=12,
            vehicle_key="01140300301",
            vehicle_id=1146,
            insured_amount_type_id=1,
            deductible_type_id=1,
            country_subdivision_id=1,
            municipality_id=42,
            vehicle_use_id=1,
            package_id=1,
        )

        with self.assertRaises(ProviderQuoteError):
            ChubbQuotePayloadBuilder.build(
                request=self.request,
                context=invalid_context,
            )

    def test_rejects_invalid_postal_code(self):
        invalid_vehicle = QuoteVehicle(
            year=2024,
            brand_code="NISSAN",
            model_code="VERSA",
            version_code="ADVANCE",
            use_code="PARTICULAR",
            postal_code="31A00",
        )

        invalid_request = QuoteRequest(
            provider_id=1,
            vehicle=invalid_vehicle,
            insured=self.request.insured,
            start_date=self.request.start_date,
            end_date=self.request.end_date,
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
        )

        with self.assertRaises(ProviderQuoteError):
            ChubbQuotePayloadBuilder.build(
                request=invalid_request,
                context=self.context,
            )
            