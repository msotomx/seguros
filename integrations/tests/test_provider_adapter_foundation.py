from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from integrations.providers.contracts import (
    QuoteAmount,
    QuoteInsured,
    QuoteRequest,
    QuoteResponse,
    QuoteVehicle,
)
from integrations.providers.exceptions import (
    ProviderUnsupportedOperationError,
)
from integrations.providers.insurance_base import (
    BaseInsuranceProviderAdapter,
)


class FakeProviderAdapter(BaseInsuranceProviderAdapter):
    provider_code = "FAKE"

    supported_operations = frozenset({
        "quote",
    })

    def authenticate(self) -> None:
        return None

    def quote(
        self,
        *,
        request: QuoteRequest,
    ) -> QuoteResponse:
        self.ensure_supported("quote")

        return QuoteResponse(
            provider_id=request.provider_id,
            provider_quote_id="FAKE-001",
            status="QUOTED",
            amount=QuoteAmount(
                net_premium=Decimal("1000.00"),
                taxes=Decimal("160.00"),
                fees=Decimal("50.00"),
                total=Decimal("1210.00"),
                currency=request.currency,
            ),
        )


class ProviderAdapterFoundationTest(SimpleTestCase):
    def setUp(self):
        self.adapter = FakeProviderAdapter()

        self.request = QuoteRequest(
            provider_id=1,
            vehicle=QuoteVehicle(
                year=2024,
                brand_code="NISSAN",
                model_code="VERSA",
                version_code="ADVANCE",
                use_code="PARTICULAR",
                postal_code="31000",
            ),
            insured=QuoteInsured(
                person_type="INDIVIDUAL",
                first_name="Miguel",
                last_name="Soto",
            ),
            start_date=date(2026, 7, 11),
            end_date=date(2027, 7, 11),
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
        )

    def test_adapter_supports_quote(self):
        self.assertTrue(
            self.adapter.supports("quote")
        )

    def test_adapter_normalizes_operation(self):
        self.assertTrue(
            self.adapter.supports(" QUOTE ")
        )

    def test_adapter_does_not_support_issue_policy(self):
        self.assertFalse(
            self.adapter.supports("issue_policy")
        )

    def test_adapter_rejects_unsupported_operation(self):
        with self.assertRaises(
            ProviderUnsupportedOperationError
        ):
            self.adapter.ensure_supported("issue_policy")

    def test_quote_returns_canonical_response(self):
        response = self.adapter.quote(
            request=self.request,
        )

        self.assertEqual(response.provider_id, 1)
        self.assertEqual(
            response.provider_quote_id,
            "FAKE-001",
        )
        self.assertEqual(response.status, "QUOTED")
        self.assertEqual(
            response.amount.net_premium,
            Decimal("1000.00"),
        )
        self.assertEqual(
            response.amount.total,
            Decimal("1210.00"),
        )
        self.assertEqual(
            response.amount.currency,
            "MXN",
        )

    def test_quote_request_contains_canonical_values(self):
        self.assertEqual(
            self.request.vehicle.use_code,
            "PARTICULAR",
        )
        self.assertEqual(
            self.request.payment_frequency_code,
            "ANNUAL",
        )
        self.assertEqual(
            self.request.coverage_code,
            "COMPREHENSIVE",
        )

    def test_request_and_response_are_immutable(self):
        with self.assertRaises(
            AttributeError
        ):
            self.request.currency = "USD"

        response = self.adapter.quote(
            request=self.request,
        )

        with self.assertRaises(
            AttributeError
        ):
            response.status = "ERROR"
            