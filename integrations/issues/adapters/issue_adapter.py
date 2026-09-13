from __future__ import annotations

from decimal import Decimal

from integrations.issues.contracts import (
    IssueResult,
    IssueRiskResult,
)
from integrations.providers.chubb.issue_contracts import (
    ChubbIssueItemResult,
    ChubbIssueResult,
)


class ChubbIssueAdapter:
    """
    Convierte el resultado específico de Chubb
    al contrato interno utilizado por IssueService.
    """

    PROVIDER_CODE = "CHUBB"
    DEFAULT_CURRENCY = "MXN"

    @classmethod
    def to_issue_result(
        cls,
        result: ChubbIssueResult,
    ) -> IssueResult:
        if not isinstance(
            result,
            ChubbIssueResult,
        ):
            raise TypeError(
                "result debe ser una instancia de "
                "ChubbIssueResult."
            )

        risks = tuple(
            cls._risk(item)
            for item in result.items
        )

        fees = sum(
            (
                risk.fees
                for risk in risks
            ),
            Decimal("0"),
        )

        taxes = sum(
            (
                risk.taxes
                for risk in risks
            ),
            Decimal("0"),
        )

        return IssueResult(
            provider_code=cls.PROVIDER_CODE,
            provider_policy_id=str(
                result.quote_policy_id
            ),
            provider_policy_key=(
                result.quote_key.strip()
                or None
            ),
            policy_number=None,
            currency=cls.DEFAULT_CURRENCY,
            net_premium=Decimal(
                str(result.net_premium_amount)
            ),
            fees=fees,
            surcharge=Decimal(
                str(result.surcharge_amount)
            ),
            discount=Decimal(
                str(result.discount_amount)
            ),
            taxes=taxes,
            total_premium=Decimal(
                str(result.total_premium_amount)
            ),
            risks=risks,
            raw_response=result.raw_response,
        )

    @staticmethod
    def _risk(
        item: ChubbIssueItemResult,
    ) -> IssueRiskResult:
        if not isinstance(
            item,
            ChubbIssueItemResult,
        ):
            raise TypeError(
                "item debe ser una instancia de "
                "ChubbIssueItemResult."
            )

        return IssueRiskResult(
            risk_number=item.number,
            net_premium=Decimal(
                str(item.net_premium_amount)
            ),
            fees=Decimal(
                str(item.right_amount)
            ),
            surcharge=Decimal(
                str(item.surcharge_amount)
            ),
            discount=Decimal(
                str(item.discount_amount)
            ),
            taxes=Decimal(
                str(item.iva_amount)
            ),
            total_premium=Decimal(
                str(item.total_premium_amount)
            ),
        )
