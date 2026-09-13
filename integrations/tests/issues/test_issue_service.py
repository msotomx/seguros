from decimal import Decimal
from unittest import TestCase

from integrations.issues.contracts import (
    IssueResult,
)
from integrations.issues.service import IssueService


class SuccessfulProvider:
    provider_code = "CHUBB"

    def issue(self, request):
        return IssueResult(
            provider_code="CHUBB",
            provider_policy_id="99007664",
            provider_policy_key="M6",
            policy_number="M6 99007664",
            currency="MXN",
            net_premium=Decimal("35247.21"),
            fees=Decimal("600.00"),
            surcharge=Decimal("0.00"),
            discount=Decimal("0.00"),
            taxes=Decimal("5735.56"),
            total_premium=Decimal("41582.77"),
        )


class FailingProvider:
    provider_code = "AXA"

    def issue(self, request):
        raise ValueError(
            "No fue posible emitir la póliza."
        )


class TimeoutProvider:
    provider_code = "GNP"

    def issue(self, request):
        raise TimeoutError(
            "El proveedor no respondió."
        )


class IssueServiceTests(TestCase):

    def test_requires_at_least_one_provider(self):
        with self.assertRaisesRegex(
            ValueError,
            "al menos un proveedor",
        ):
            IssueService([])

    def test_rejects_duplicate_provider_codes(self):
        with self.assertRaisesRegex(
            ValueError,
            "más de un proveedor",
        ):
            IssueService(
                [
                    SuccessfulProvider(),
                    SuccessfulProvider(),
                ]
            )

    def test_issue_one_returns_successful_attempt(self):
        service = IssueService(
            [SuccessfulProvider()]
        )

        attempt = service.issue_one(
            "chubb",
            request={},
        )

        self.assertTrue(
            attempt.success
        )
        self.assertIsNotNone(
            attempt.result
        )
        self.assertIsNone(
            attempt.error
        )
        self.assertEqual(
            attempt.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            attempt.result.provider_policy_id,
            "99007664",
        )
        self.assertEqual(
            attempt.result.provider_policy_key,
            "M6",
        )
        self.assertEqual(
            attempt.result.total_premium,
            Decimal("41582.77"),
        )

    def test_issue_one_normalizes_provider_code(self):
        service = IssueService(
            [SuccessfulProvider()]
        )

        attempt = service.issue_one(
            "  chubb  ",
            request={},
        )

        self.assertEqual(
            attempt.provider_code,
            "CHUBB",
        )

    def test_issue_one_returns_failed_attempt(self):
        service = IssueService(
            [FailingProvider()]
        )

        attempt = service.issue_one(
            "AXA",
            request={},
        )

        self.assertFalse(
            attempt.success
        )
        self.assertIsNone(
            attempt.result
        )
        self.assertIsNotNone(
            attempt.error
        )
        self.assertEqual(
            attempt.error.error_type,
            "ValueError",
        )
        self.assertIn(
            "No fue posible emitir",
            attempt.error.message,
        )

    def test_timeout_is_retryable(self):
        service = IssueService(
            [TimeoutProvider()]
        )

        attempt = service.issue_one(
            "GNP",
            request={},
        )

        self.assertFalse(
            attempt.success
        )
        self.assertTrue(
            attempt.error.retryable
        )

    def test_unregistered_provider_is_rejected(self):
        service = IssueService(
            [SuccessfulProvider()]
        )

        with self.assertRaisesRegex(
            ValueError,
            "no está registrado",
        ):
            service.issue_one(
                "MAPFRE",
                request={},
            )

    def test_provider_code_must_match_result(self):
        class InvalidProvider:
            provider_code = "CHUBB"

            def issue(self, request):
                return IssueResult(
                    provider_code="AXA",
                    provider_policy_id="123",
                    provider_policy_key="A1",
                    policy_number="A1 123",
                    currency="MXN",
                    net_premium=Decimal("800.00"),
                    fees=Decimal("50.00"),
                    surcharge=Decimal("0.00"),
                    discount=Decimal("0.00"),
                    taxes=Decimal("150.00"),
                    total_premium=Decimal("1000.00"),
                )

        service = IssueService(
            [InvalidProvider()]
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_code distinto",
        ):
            service.issue_one(
                "CHUBB",
                request={},
            )
