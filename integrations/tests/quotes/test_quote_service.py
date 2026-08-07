from decimal import Decimal
from unittest import TestCase

from integrations.quotes.contracts import (
    QuoteResult,
)
from integrations.quotes.service import QuoteService


class SuccessfulProvider:
    provider_code = "CHUBB"

    def quote(self, request):
        return QuoteResult(
            provider_code="CHUBB",
            provider_quote_id="QUOTE-123",
            reference="SWITCHH-001",
            currency="MXN",
            net_premium=Decimal("10000.00"),
            fees=Decimal("500.00"),
            taxes=Decimal("2000.50"),
            total_premium=Decimal("12500.50"),
        )

class ExpensiveProvider:
    provider_code = "QUALITAS"

    def quote(self, request):
        return QuoteResult(
            provider_code="QUALITAS",
            provider_quote_id="QUOTE-456",
            reference="SWITCHH-001",
            currency="MXN",
            net_premium=Decimal("11500.00"),
            fees=Decimal("500.00"),
            taxes=Decimal("2200.00"),
            total_premium=Decimal("14200.00"),
        )


class FailingProvider:
    provider_code = "AXA"

    def quote(self, request):
        raise ValueError(
            "No fue posible calcular la cotización."
        )


class TimeoutProvider:
    provider_code = "GNP"

    def quote(self, request):
        raise TimeoutError(
            "El proveedor no respondió."
        )


class QuoteServiceTests(TestCase):
    def test_requires_at_least_one_provider(self):
        with self.assertRaisesRegex(
            ValueError,
            "al menos un proveedor",
        ):
            QuoteService([])

    def test_rejects_duplicate_provider_codes(self):
        with self.assertRaisesRegex(
            ValueError,
            "más de un proveedor",
        ):
            QuoteService(
                [
                    SuccessfulProvider(),
                    SuccessfulProvider(),
                ]
            )

    def test_quote_one_returns_successful_attempt(self):
        service = QuoteService(
            [SuccessfulProvider()]
        )

        attempt = service.quote_one(
            "chubb",
            request={"vehicle": "test"},
        )

        self.assertTrue(attempt.success)
        self.assertIsNotNone(attempt.result)
        self.assertIsNone(attempt.error)
        self.assertEqual(
            attempt.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            attempt.result.total_premium,
            Decimal("12500.50"),
        )

    def test_quote_one_normalizes_provider_code(self):
        service = QuoteService(
            [SuccessfulProvider()]
        )

        attempt = service.quote_one(
            "  chubb  ",
            request={},
        )

        self.assertEqual(
            attempt.provider_code,
            "CHUBB",
        )

    def test_quote_one_returns_failed_attempt(self):
        service = QuoteService(
            [FailingProvider()]
        )

        attempt = service.quote_one(
            "AXA",
            request={},
        )

        self.assertFalse(attempt.success)
        self.assertIsNone(attempt.result)
        self.assertIsNotNone(attempt.error)
        self.assertEqual(
            attempt.error.error_type,
            "ValueError",
        )
        self.assertIn(
            "No fue posible",
            attempt.error.message,
        )

    def test_timeout_is_retryable(self):
        service = QuoteService(
            [TimeoutProvider()]
        )

        attempt = service.quote_one(
            "GNP",
            request={},
        )

        self.assertFalse(attempt.success)
        self.assertTrue(
            attempt.error.retryable
        )

    def test_quote_many_isolates_provider_errors(self):
        service = QuoteService(
            [
                SuccessfulProvider(),
                FailingProvider(),
            ]
        )

        batch = service.quote_many(
            {
                "CHUBB": {},
                "AXA": {},
            }
        )

        self.assertEqual(
            len(batch.attempts),
            2,
        )
        self.assertEqual(
            len(batch.successful),
            1,
        )
        self.assertEqual(
            len(batch.failed),
            1,
        )
        self.assertTrue(batch.has_results)

    def test_quote_many_supports_fail_fast(self):
        service = QuoteService(
            [
                FailingProvider(),
                SuccessfulProvider(),
            ]
        )

        batch = service.quote_many(
            {
                "AXA": {},
                "CHUBB": {},
            },
            fail_fast=True,
        )

        self.assertEqual(
            len(batch.attempts),
            1,
        )
        self.assertFalse(
            batch.attempts[0].success
        )

    def test_best_price_returns_cheapest_result(self):
        service = QuoteService(
            [
                SuccessfulProvider(),
                ExpensiveProvider(),
            ]
        )

        batch = service.quote_many(
            {
                "CHUBB": {},
                "QUALITAS": {},
            }
        )

        self.assertIsNotNone(
            batch.best_price
        )
        self.assertEqual(
            batch.best_price.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            batch.best_price.total_premium,
            Decimal("12500.50"),
        )

    def test_unregistered_provider_is_rejected(self):
        service = QuoteService(
            [SuccessfulProvider()]
        )

        with self.assertRaisesRegex(
            ValueError,
            "no está registrado",
        ):
            service.quote_one(
                "MAPFRE",
                request={},
            )

    def test_provider_code_must_match_result(self):
        class InvalidProvider:
            provider_code = "CHUBB"

            def quote(self, request):
                return QuoteResult(
                    provider_code="AXA",
                    provider_quote_id=None,
                    reference=None,
                    currency="MXN",
                    net_premium=Decimal("800.00"),
                    fees=Decimal("50.00"),
                    taxes=Decimal("150.00"),
                    total_premium=Decimal("1000.00"),
                )

        service = QuoteService(
            [InvalidProvider()]
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_code distinto",
        ):
            service.quote_one(
                "CHUBB",
                request={},
            )
