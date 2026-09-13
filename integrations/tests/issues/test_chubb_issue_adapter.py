from decimal import Decimal
from unittest import TestCase

from integrations.issues.adapters.issue_adapter import (
    ChubbIssueAdapter,
)
from integrations.providers.chubb.issue_contracts import (
    ChubbIssueItemResult,
    ChubbIssueResult,
)


class ChubbIssueAdapterTests(TestCase):

    def test_to_issue_result_maps_policy_and_premiums(self):
        chubb_result = ChubbIssueResult(
            quote_key="M6",
            quote_policy_id=99007664,
            net_premium_amount=35247.21,
            bonification_amount=0.0,
            surcharge_amount=0.0,
            discount_amount=0.0,
            total_premium_amount=41582.77,
            insured_id=18683522,
            insured_address_id=1410484013,
            items=(
                ChubbIssueItemResult(
                    number=1,
                    net_premium_amount=35247.21,
                    right_amount=600.0,
                    discount_amount=0.0,
                    surcharge_amount=0.0,
                    iva_amount=5735.56,
                    total_premium_amount=41582.77,
                ),
            ),
            raw_response={
                "success": True,
            },
        )

        result = ChubbIssueAdapter.to_issue_result(
            chubb_result
        )

        self.assertEqual(
            result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            result.provider_policy_id,
            "99007664",
        )
        self.assertEqual(
            result.provider_policy_key,
            "M6",
        )
        self.assertIsNone(
            result.policy_number
        )

        self.assertEqual(
            result.currency,
            "MXN",
        )
        self.assertEqual(
            result.net_premium,
            Decimal("35247.21"),
        )
        self.assertEqual(
            result.fees,
            Decimal("600.0"),
        )
        self.assertEqual(
            result.surcharge,
            Decimal("0.0"),
        )
        self.assertEqual(
            result.discount,
            Decimal("0.0"),
        )
        self.assertEqual(
            result.taxes,
            Decimal("5735.56"),
        )
        self.assertEqual(
            result.total_premium,
            Decimal("41582.77"),
        )

    def test_to_issue_result_maps_risk_premiums(self):
        chubb_result = ChubbIssueResult(
            quote_key="M6",
            quote_policy_id=99007664,
            net_premium_amount=35247.21,
            bonification_amount=0.0,
            surcharge_amount=0.0,
            discount_amount=0.0,
            total_premium_amount=41582.77,
            insured_id=18683522,
            insured_address_id=1410484013,
            items=(
                ChubbIssueItemResult(
                    number=1,
                    net_premium_amount=35247.21,
                    right_amount=600.0,
                    discount_amount=0.0,
                    surcharge_amount=0.0,
                    iva_amount=5735.56,
                    total_premium_amount=41582.77,
                ),
            ),
            raw_response={},
        )

        result = ChubbIssueAdapter.to_issue_result(
            chubb_result
        )

        self.assertEqual(
            len(result.risks),
            1,
        )

        risk = result.risks[0]

        self.assertEqual(
            risk.risk_number,
            1,
        )
        self.assertEqual(
            risk.net_premium,
            Decimal("35247.21"),
        )
        self.assertEqual(
            risk.fees,
            Decimal("600.0"),
        )
        self.assertEqual(
            risk.taxes,
            Decimal("5735.56"),
        )
        self.assertEqual(
            risk.total_premium,
            Decimal("41582.77"),
        )

    def test_to_issue_result_aggregates_fees_and_taxes(self):
        chubb_result = ChubbIssueResult(
            quote_key="M6",
            quote_policy_id=99007664,
            net_premium_amount=30000.0,
            bonification_amount=0.0,
            surcharge_amount=0.0,
            discount_amount=0.0,
            total_premium_amount=36000.0,
            insured_id=18683522,
            insured_address_id=1410484013,
            items=(
                ChubbIssueItemResult(
                    number=1,
                    net_premium_amount=15000.0,
                    right_amount=300.0,
                    discount_amount=0.0,
                    surcharge_amount=0.0,
                    iva_amount=2400.0,
                    total_premium_amount=17700.0,
                ),
                ChubbIssueItemResult(
                    number=2,
                    net_premium_amount=15000.0,
                    right_amount=400.0,
                    discount_amount=0.0,
                    surcharge_amount=0.0,
                    iva_amount=2500.0,
                    total_premium_amount=17900.0,
                ),
            ),
            raw_response={},
        )

        result = ChubbIssueAdapter.to_issue_result(
            chubb_result
        )

        self.assertEqual(
            result.fees,
            Decimal("700.0"),
        )
        self.assertEqual(
            result.taxes,
            Decimal("4900.0"),
        )

    def test_to_issue_result_does_not_invent_policy_number(self):
        chubb_result = ChubbIssueResult(
            quote_key="M6",
            quote_policy_id=99007664,
            net_premium_amount=100.0,
            bonification_amount=0.0,
            surcharge_amount=0.0,
            discount_amount=0.0,
            total_premium_amount=116.0,
            insured_id=1,
            insured_address_id=2,
            items=(
                ChubbIssueItemResult(
                    number=1,
                    net_premium_amount=100.0,
                    right_amount=0.0,
                    discount_amount=0.0,
                    surcharge_amount=0.0,
                    iva_amount=16.0,
                    total_premium_amount=116.0,
                ),
            ),
            raw_response={},
        )

        result = ChubbIssueAdapter.to_issue_result(
            chubb_result
        )

        self.assertIsNone(
            result.policy_number
        )
        self.assertEqual(
            result.provider_policy_key,
            "M6",
        )
        self.assertEqual(
            result.provider_policy_id,
            "99007664",
        )
