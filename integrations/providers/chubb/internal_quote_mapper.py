from __future__ import annotations

from collections.abc import Mapping

from integrations.quotes.contracts import (
    InternalQuoteRequest,
    QuoteCoverageRequest,
    QuoteDiscountRequest,
    QuotePackageRequest,
    QuoteRisk,
)

from .quote_contracts import (
    ChubbCreateQuoteRequest,
    ChubbQuoteCoverageRequest,
    ChubbQuoteDiscountRequest,
    ChubbQuoteDriverRequest,
    ChubbQuoteItemRequest,
    ChubbQuotePackageRequest,
    ChubbQuotePaymentTypeRequest,
    ChubbQuoteVehicleRequest,
)


class ChubbInternalQuoteRequestMapper:
    """
    Convierte el contrato interno del ERP al contrato específico de Chubb.

    Los identificadores propios de Chubb se reciben ya resueltos mediante
    configuración o equivalencias de catálogo. El mapper no consulta ORM,
    configuración ni catálogos.
    """

    def __init__(
        self,
        *,
        product_id: int,
        business_profile_id: int,
        agent_id: str,
        conduit_id: int,
        grouping_id: int,
        rate_id: int,
        calculation_type_id: int,
        currency_id: int,
        payment_type_id: int,
        insured_amount_type_id: int,
        deductible_type_id: int,
        nadasc: bool,
        gender_ids: Mapping[str, int],
    ) -> None:
        self._product_id = product_id
        self._business_profile_id = business_profile_id
        self._agent_id = agent_id
        self._conduit_id = conduit_id
        self._grouping_id = grouping_id
        self._rate_id = rate_id
        self._calculation_type_id = calculation_type_id
        self._currency_id = currency_id
        self._payment_type_id = payment_type_id
        self._insured_amount_type_id = insured_amount_type_id
        self._deductible_type_id = deductible_type_id
        self._nadasc = nadasc

        self._gender_ids = {
            str(code).strip().upper(): int(external_id)
            for code, external_id in gender_ids.items()
        }


    def create_quote(
        self,
        request: InternalQuoteRequest,
    ) -> ChubbCreateQuoteRequest:
        if not isinstance(request, InternalQuoteRequest):
            raise TypeError(
                "request debe ser una instancia de InternalQuoteRequest."
            )

        return ChubbCreateQuoteRequest(
            product_id=self._product_id,
            business_profile_id=self._business_profile_id,
            agent_id=self._agent_id,
            conduit_id=self._conduit_id,
            grouping_id=self._grouping_id,
            rate_id=self._rate_id,
            effective_date=request.effective_date,
            expiration_date=request.expiration_date,
            calculation_type_id=self._calculation_type_id,
            currency_id=self._currency_id,
            reference=request.reference,
            prospect_name=request.prospect_name,
            payment_types=(
                ChubbQuotePaymentTypeRequest(
                    payment_type_id=self._payment_type_id,
                ),
            ),
            items=tuple(
                self._risk(
                    risk=risk,
                    risk_number=index,
                )
                for index, risk in enumerate(
                    request.risks,
                    start=1,
                )
            ),
        )

    def _risk(
        self,
        *,
        risk: QuoteRisk,
        risk_number: int,
    ) -> ChubbQuoteItemRequest:
        return ChubbQuoteItemRequest(
            # En Create Quote, cero representa un riesgo nuevo.
            risk_id=0,
            risk_number=risk_number,
            vehicle=ChubbQuoteVehicleRequest(
                vehicle_key=risk.vehicle.vehicle_key,
                insured_amount_type_id=(
                    self._insured_amount_type_id
                ),
                deductible_type_id=self._deductible_type_id,
                year=risk.vehicle.year,
                country_subdivision_id=int(
                    risk.vehicle.state_code
                ),
                municipality_id=int(
                    risk.vehicle.municipality_code
                ),
                use_id=int(
                    risk.vehicle.use_code
                ),
                garage_use=risk.vehicle.garage,
                nadasc=self._nadasc,
                reference=risk.reference,
                plate=risk.vehicle.plate or "",
                age=risk.driver.age,
                gender_id=self._gender_id(
                    risk.driver.gender
                ),
                driver=ChubbQuoteDriverRequest(),
            ),
            packages=tuple(
                self._package(package)
                for package in risk.packages
            ),
            discounts=tuple(
                self._discount(discount)
                for discount in risk.discounts
            ),
        )

    def _package(
        self,
        package: QuotePackageRequest,
    ) -> ChubbQuotePackageRequest:
        return ChubbQuotePackageRequest(
            package_id=int(package.code),
            selected=package.selected,
            coverages=tuple(
                self._coverage(coverage)
                for coverage in package.coverages
            ),
        )

    def _coverage(
        self,
        coverage: QuoteCoverageRequest,
    ) -> ChubbQuoteCoverageRequest:
        return ChubbQuoteCoverageRequest(
            coverage_id=int(coverage.code),
            insurance_amount=float(
                coverage.insured_amount or 0
            ),
            deductible_type_id=self._deductible_type_id,
            deductible_value=float(
                coverage.deductible or 0
            ),
        )

    @staticmethod
    def _discount(
        discount: QuoteDiscountRequest,
    ) -> ChubbQuoteDiscountRequest:
        return ChubbQuoteDiscountRequest(
            discount_type_id=int(discount.code),
            discount_tag=discount.code,
            discount_percentage=float(
                discount.percentage
            ),
        )

    def _gender_id(
        self,
        gender: str,
    ) -> int:
        normalized = str(gender).strip().upper()

        try:
            return self._gender_ids[normalized]
        except KeyError as exc:
            raise ValueError(
                f"Género no configurado para Chubb: {gender}"
            ) from exc
