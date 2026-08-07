from __future__ import annotations

from decimal import Decimal

from integrations.quotes.contracts import (
    QuoteCoverage,
    QuoteOption,
    QuoteResult,
    QuoteRiskResult,
)

from integrations.providers.chubb.quote_contracts import (
    ChubbCreateQuoteResult,
    ChubbQuoteCoverageResult,
    ChubbQuotePackageResult,
    ChubbQuoteItemResult,
)


class ChubbQuoteAdapter:
    """
    Convierte el resultado específico de Chubb al modelo interno
    utilizado por QuoteService.
    """

    PROVIDER_CODE = "CHUBB"
    DEFAULT_CURRENCY = "MXN"

    @classmethod
    def to_quote_result(
        cls,
        result: ChubbCreateQuoteResult,
    ) -> QuoteResult:

        risks = tuple(
            cls._risk(item)
            for item in result.items
        )

        options = tuple(
            option
            for risk in risks
            for option in risk.options
        )

        return QuoteResult(
            provider_code=cls.PROVIDER_CODE,
            provider_quote_id=str(result.quote_id),
            provider_quote_version_id=str(
                result.quote_version_id
            ),
            reference=None,
            currency=cls.DEFAULT_CURRENCY,

            net_premium=Decimal(
                str(result.base_net_premium)
            ),
            fees=Decimal(
                str(result.fee_amount)
            ),
            taxes=Decimal(
                str(result.tax_amount)
            ),
            total_premium=Decimal(
                str(result.total_premium_amount)
            ),

            options=options,
            risks=risks,

            raw_response=result.raw_response,
        )


    @classmethod
    def _risk(
        cls,
        item: ChubbQuoteItemResult,
    ) -> QuoteRiskResult:
        return QuoteRiskResult(
            reference=None,
            provider_risk_id=str(item.risk_id),
            risk_number=item.risk_number,
            vehicle_key=item.vehicle_key,
            options=tuple(
                cls._package(package)
                for package in item.packages
            ),
        )


    @classmethod
    def _package(
        cls,
        package: ChubbQuotePackageResult,
    ) -> QuoteOption:

        coverages = tuple(
            cls._coverage(c)
            for c in package.coverages
        )

        return QuoteOption(
            code=str(package.package_id),
            provider_package_id=package.package_id,
            name=(
                package.description
                or f"Paquete {package.package_id}"
            ),

            total_premium=Decimal(
                str(package.total_premium)
            ),

            currency=cls.DEFAULT_CURRENCY,
            selected=package.selected,
            coverages=coverages,
        )


    @staticmethod
    def _coverage(
        coverage: ChubbQuoteCoverageResult,
    ) -> QuoteCoverage:

        return QuoteCoverage(
            code=str(
                coverage.coverage_id
            ),

            name=(
                coverage.custom_name
                or coverage.description
            ),

            insured_amount=(
                None
                if coverage.insured_amount is None
                else Decimal(
                    str(
                        coverage.insured_amount
                    )
                )
            ),

            deductible=(
                None
                if coverage.deductible_value is None
                else Decimal(
                    str(
                        coverage.deductible_value
                    )
                )
            ),

            premium=Decimal(
                str(
                    coverage.premium
                )
            ),
        )
