from decimal import Decimal
from unittest import TestCase

from integrations.providers.chubb.quote_contracts import (
    ChubbCreateQuoteResult,
    ChubbQuoteCoverageResult,
    ChubbQuoteItemResult,
    ChubbQuotePackageResult,
)
from integrations.quotes.adapters.quote_adapter import (
    ChubbQuoteAdapter,
)
from integrations.quotes.contracts import (
    QuoteCoverage,
    QuoteOption,
    QuoteResult,
    QuoteRiskResult,
)


class ChubbQuoteAdapterTests(TestCase):
    def setUp(self) -> None:
        self.coverage = ChubbQuoteCoverageResult(
            coverage_id=101,
            description="Daños materiales",
            custom_name=None,
            insured_amount=250000.00,
            premium=1234.56,
            deductible_type_id=1,
            deductible_value=5.00,
            selected=True,
        )

        self.package = ChubbQuotePackageResult(
            package_id=201,
            description="Cobertura amplia",
            total_premium=32106.6911,
            selected=True,
            coverages=(
                self.coverage,
            ),
        )

        self.item = ChubbQuoteItemResult(
            risk_id=301,
            risk_number=1,
            vehicle_key="03070300101",
            packages=(
                self.package,
            ),
        )

        self.raw_response = {
            "isSuccess": True,
            "responseData": {
                "quoteId": 401,
                "quoteVersionId": 402,
            },
        }

        self.result = ChubbCreateQuoteResult(
            quote_id=401,
            quote_version_id=402,
            base_net_premium=27078.182,
            base_net_premium_without_discount=27078.182,
            discounts=(),
            surcharge_percentage=0.0,
            surcharge_amount=0.0,
            fee_amount=600.0,
            tax_percentage=None,
            tax_amount=4428.5091,
            total_premium_amount=32106.6911,
            commission_percentage=None,
            commission_amount=None,
            surcharge_commission_amount=None,
            items=(
                self.item,
            ),
            raw_response=self.raw_response,
        )

    def test_to_quote_result_maps_main_amounts(self):
        quote_result = ChubbQuoteAdapter.to_quote_result(
            self.result
        )

        self.assertEqual(
            quote_result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            quote_result.provider_quote_id,
            "401",
        )
        self.assertEqual(
            quote_result.net_premium,
            Decimal("27078.182"),
        )
        self.assertEqual(
            quote_result.fees,
            Decimal("600.0"),
        )
        self.assertEqual(
            quote_result.taxes,
            Decimal("4428.5091"),
        )
        self.assertEqual(
            quote_result.total_premium,
            Decimal("32106.6911"),
        )
        self.assertEqual(
            quote_result.raw_response,
            self.raw_response,
        )

    def test_to_quote_result_maps_package(self):
        quote_result = ChubbQuoteAdapter.to_quote_result(
            self.result
        )

        self.assertEqual(
            len(quote_result.options),
            1,
        )

        option = quote_result.options[0]

        self.assertEqual(option.code, "201")
        self.assertEqual(
            option.provider_package_id,
            201,
        )
        self.assertEqual(
            option.name,
            "Cobertura amplia",
        )
        self.assertEqual(
            option.total_premium,
            Decimal("32106.6911"),
        )
        self.assertTrue(option.selected)

    def test_to_quote_result_maps_coverage(self):
        quote_result = ChubbQuoteAdapter.to_quote_result(
            self.result
        )

        coverage = (
            quote_result.options[0]
            .coverages[0]
        )

        self.assertEqual(coverage.code, "101")
        self.assertEqual(
            coverage.name,
            "Daños materiales",
        )
        self.assertEqual(
            coverage.insured_amount,
            Decimal("250000.0"),
        )
        self.assertEqual(
            coverage.deductible,
            Decimal("5.0"),
        )
        self.assertEqual(
            coverage.premium,
            Decimal("1234.56"),
        )

    def test_to_quote_result_prefers_custom_coverage_name(self):
        custom_coverage = ChubbQuoteCoverageResult(
            coverage_id=101,
            description="Daños materiales",
            custom_name="Cobertura especial",
            insured_amount=250000.00,
            premium=1234.56,
            deductible_type_id=1,
            deductible_value=5.00,
            selected=True,
        )

        package = ChubbQuotePackageResult(
            package_id=201,
            description="Cobertura amplia",
            total_premium=32106.6911,
            selected=True,
            coverages=(
                custom_coverage,
            ),
        )

        result = ChubbCreateQuoteResult(
            quote_id=self.result.quote_id,
            quote_version_id=self.result.quote_version_id,
            base_net_premium=self.result.base_net_premium,
            base_net_premium_without_discount=(
                self.result.base_net_premium_without_discount
            ),
            discounts=self.result.discounts,
            surcharge_percentage=(
                self.result.surcharge_percentage
            ),
            surcharge_amount=self.result.surcharge_amount,
            fee_amount=self.result.fee_amount,
            tax_percentage=self.result.tax_percentage,
            tax_amount=self.result.tax_amount,
            total_premium_amount=(
                self.result.total_premium_amount
            ),
            commission_percentage=(
                self.result.commission_percentage
            ),
            commission_amount=self.result.commission_amount,
            surcharge_commission_amount=(
                self.result.surcharge_commission_amount
            ),
            items=(
                ChubbQuoteItemResult(
                    risk_id=301,
                    risk_number=1,
                    vehicle_key="03070300101",
                    packages=(
                        package,
                    ),
                ),
            ),
            raw_response=self.result.raw_response,
        )

        quote_result = ChubbQuoteAdapter.to_quote_result(
            result
        )

        self.assertEqual(
            quote_result.options[0].coverages[0].name,
            "Cobertura especial",
        )

    def test_to_quote_result_preserves_null_coverage_values(self):
        coverage_with_nulls = ChubbQuoteCoverageResult(
            coverage_id=101,
            description="Responsabilidad civil",
            custom_name=None,
            insured_amount=None,
            premium=0.0,
            deductible_type_id=None,
            deductible_value=None,
            selected=True,
        )

        package = ChubbQuotePackageResult(
            package_id=201,
            description=None,
            total_premium=0.0,
            selected=False,
            coverages=(
                coverage_with_nulls,
            ),
        )

        result = ChubbCreateQuoteResult(
            quote_id=self.result.quote_id,
            quote_version_id=self.result.quote_version_id,
            base_net_premium=self.result.base_net_premium,
            base_net_premium_without_discount=(
                self.result.base_net_premium_without_discount
            ),
            discounts=self.result.discounts,
            surcharge_percentage=(
                self.result.surcharge_percentage
            ),
            surcharge_amount=self.result.surcharge_amount,
            fee_amount=self.result.fee_amount,
            tax_percentage=self.result.tax_percentage,
            tax_amount=self.result.tax_amount,
            total_premium_amount=(
                self.result.total_premium_amount
            ),
            commission_percentage=(
                self.result.commission_percentage
            ),
            commission_amount=self.result.commission_amount,
            surcharge_commission_amount=(
                self.result.surcharge_commission_amount
            ),
            items=(
                ChubbQuoteItemResult(
                    risk_id=301,
                    risk_number=1,
                    vehicle_key="03070300101",
                    packages=(
                        package,
                    ),
                ),
            ),
            raw_response=self.result.raw_response,
        )

        quote_result = ChubbQuoteAdapter.to_quote_result(
            result
        )

        option = quote_result.options[0]
        coverage = option.coverages[0]

        self.assertEqual(
            option.name,
            "Paquete 201",
        )
        self.assertFalse(option.selected)
        self.assertIsNone(coverage.insured_amount)
        self.assertIsNone(coverage.deductible)

    def test_to_quote_result_maps_quote_version_id(self):
        quote_result = ChubbQuoteAdapter.to_quote_result(
            self.result
        )

        self.assertEqual(
            quote_result.provider_quote_version_id,
            "402",
        )

    def test_to_quote_result_maps_risk(self):
        quote_result = ChubbQuoteAdapter.to_quote_result(
            self.result
        )

        self.assertEqual(
            len(quote_result.risks),
            1,
        )

        risk = quote_result.risks[0]

        self.assertIsNone(risk.reference)
        self.assertEqual(
            risk.provider_risk_id,
            "301",
        )
        self.assertEqual(
            risk.risk_number,
            1,
        )
        self.assertEqual(
            risk.vehicle_key,
            "03070300101",
        )
        self.assertEqual(
            len(risk.options),
            1,
        )
        self.assertEqual(
            risk.options[0].provider_package_id,
            201,
        )

    def test_to_quote_result_preserves_flat_options(self):
        quote_result = ChubbQuoteAdapter.to_quote_result(
            self.result
        )

        self.assertEqual(
            quote_result.options,
            quote_result.risks[0].options,
        )

    def test_to_quote_result_keeps_packages_grouped_by_risk(self):
        second_package = ChubbQuotePackageResult(
            package_id=202,
            description="Cobertura limitada",
            total_premium=21000.00,
            selected=False,
            coverages=(),
        )

        second_item = ChubbQuoteItemResult(
            risk_id=302,
            risk_number=2,
            vehicle_key="03070300102",
            packages=(
                second_package,
            ),
        )

        result = ChubbCreateQuoteResult(
            quote_id=self.result.quote_id,
            quote_version_id=self.result.quote_version_id,
            base_net_premium=self.result.base_net_premium,
            base_net_premium_without_discount=(
                self.result.base_net_premium_without_discount
            ),
            discounts=self.result.discounts,
            surcharge_percentage=(
                self.result.surcharge_percentage
            ),
            surcharge_amount=self.result.surcharge_amount,
            fee_amount=self.result.fee_amount,
            tax_percentage=self.result.tax_percentage,
            tax_amount=self.result.tax_amount,
            total_premium_amount=(
                self.result.total_premium_amount
            ),
            commission_percentage=(
                self.result.commission_percentage
            ),
            commission_amount=self.result.commission_amount,
            surcharge_commission_amount=(
                self.result.surcharge_commission_amount
            ),
            items=(
                self.item,
                second_item,
            ),
            raw_response=self.result.raw_response,
        )

        quote_result = ChubbQuoteAdapter.to_quote_result(
            result
        )

        self.assertEqual(
            len(quote_result.risks),
            2,
        )
        self.assertEqual(
            quote_result.risks[0].options[0].code,
            "201",
        )
        self.assertEqual(
            quote_result.risks[1].options[0].code,
            "202",
        )
        self.assertEqual(
            [option.code for option in quote_result.options],
            ["201", "202"],
        )

    def test_to_quote_result_supports_empty_items(self):
        result = ChubbCreateQuoteResult(
            quote_id=self.result.quote_id,
            quote_version_id=self.result.quote_version_id,
            base_net_premium=self.result.base_net_premium,
            base_net_premium_without_discount=(
                self.result.base_net_premium_without_discount
            ),
            discounts=self.result.discounts,
            surcharge_percentage=(
                self.result.surcharge_percentage
            ),
            surcharge_amount=self.result.surcharge_amount,
            fee_amount=self.result.fee_amount,
            tax_percentage=self.result.tax_percentage,
            tax_amount=self.result.tax_amount,
            total_premium_amount=(
                self.result.total_premium_amount
            ),
            commission_percentage=(
                self.result.commission_percentage
            ),
            commission_amount=self.result.commission_amount,
            surcharge_commission_amount=(
                self.result.surcharge_commission_amount
            ),
            items=(),
            raw_response=self.result.raw_response,
        )

        quote_result = ChubbQuoteAdapter.to_quote_result(
            result
        )

        self.assertEqual(
            quote_result.risks,
            (),
        )
        self.assertEqual(
            quote_result.options,
            (),
        )

