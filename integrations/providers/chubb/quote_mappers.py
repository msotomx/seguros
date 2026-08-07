from __future__ import annotations

import math
from datetime import date
from typing import Any, Mapping

from .quote_contracts import (
    ChubbCreateQuoteRequest,
    ChubbCreateQuoteResult,
    ChubbQuoteCoverageRequest,
    ChubbQuoteCoverageResult,
    ChubbQuoteDiscountRequest,
    ChubbQuoteDiscountResult,
    ChubbQuoteDriverRequest,
    ChubbQuoteItemRequest,
    ChubbQuoteItemResult,
    ChubbQuotePackageRequest,
    ChubbQuotePackageResult,
    ChubbQuotePaymentTypeRequest,
    ChubbQuoteVehicleRequest,
)

class ChubbQuoteRequestMapper:
    """
    Valida y serializa los contratos internos de Create Quote al formato
    exacto esperado por la API de Chubb.
    """

    @classmethod
    def create_quote(
        cls,
        request: ChubbCreateQuoteRequest,
    ) -> dict[str, Any]:
        if not isinstance(request, ChubbCreateQuoteRequest):
            raise ValueError(
                "request debe ser una instancia de ChubbCreateQuoteRequest."
            )

        cls._validate_create_quote_request(request)

        return {
            "productId": request.product_id,
            "businessprofileId": request.business_profile_id,
            "agentId": request.agent_id.strip(),
            "conduitId": request.conduit_id,
            "groupingId": request.grouping_id,
            "rateId": request.rate_id,
            "effectiveDate": request.effective_date.isoformat(),
            "expirationDate": request.expiration_date.isoformat(),
            "calculationTypeId": request.calculation_type_id,
            "currencyId": request.currency_id,
            "reference": request.reference.strip(),
            "prospectName": request.prospect_name.strip(),
            "paymentTypes": [
                cls._payment_type(payment_type)
                for payment_type in request.payment_types
            ],
            "items": [
                cls._item(item)
                for item in request.items
            ],
        }

    @classmethod
    def _item(
        cls,
        item: ChubbQuoteItemRequest,
    ) -> dict[str, Any]:
        if not isinstance(item, ChubbQuoteItemRequest):
            raise ValueError(
                "Cada item debe ser ChubbQuoteItemRequest."
            )

        cls._require_non_negative_int(item.risk_id, "risk_id")
        cls._require_positive_int(item.risk_number, "risk_number")

        if not isinstance(item.vehicle, ChubbQuoteVehicleRequest):
            raise ValueError(
                "item.vehicle debe ser ChubbQuoteVehicleRequest."
            )

        if not isinstance(item.discounts, tuple):
            raise ValueError(
                "item.discounts debe ser una tupla."
            )

        if not isinstance(item.packages, tuple):
            raise ValueError(
                "item.packages debe ser una tupla."
            )

        if not item.packages:
            raise ValueError(
                "Cada item debe contener al menos un paquete."
            )

        return {
            "riskId": item.risk_id,
            "riskNumber": item.risk_number,
            "discount": [
                cls._discount(discount)
                for discount in item.discounts
            ],
            "vehicle": cls._vehicle(item.vehicle),
            "packages": [
                cls._package(package)
                for package in item.packages
            ],
        }
    
    @classmethod
    def _package(
        cls,
        package: ChubbQuotePackageRequest,
    ) -> dict[str, Any]:
        if not isinstance(package, ChubbQuotePackageRequest):
            raise ValueError(
                "Cada package debe ser ChubbQuotePackageRequest."
            )

        cls._require_positive_int(
            package.package_id,
            "package_id",
        )
        cls._require_bool(
            package.selected,
            "package.selected",
        )

        if not isinstance(package.coverages, tuple):
            raise ValueError(
                "package.coverages debe ser una tupla."
            )

        return {
            "packageId": package.package_id,
            "selected": package.selected,
            "coverages": [
                cls._coverage(coverage)
                for coverage in package.coverages
            ],
        }

    @classmethod
    def _coverage(
        cls,
        coverage: ChubbQuoteCoverageRequest,
    ) -> dict[str, Any]:
        if not isinstance(coverage, ChubbQuoteCoverageRequest):
            raise ValueError(
                "Cada coverage debe ser "
                "ChubbQuoteCoverageRequest."
            )

        cls._require_positive_int(
            coverage.coverage_id,
            "coverage_id",
        )
        cls._require_non_negative_number(
            coverage.insurance_amount,
            "insurance_amount",
        )
        cls._require_positive_int(
            coverage.deductible_type_id,
            "coverage.deductible_type_id",
        )
        cls._require_non_negative_number(
            coverage.deductible_value,
            "deductible_value",
        )
        cls._require_string(
            coverage.coverage_custom_description,
            "coverage_custom_description",
        )

        return {
            "coverageId": coverage.coverage_id,
            "insuranceAmount": float(
                coverage.insurance_amount
            ),
            "deductibleTypeId": (
                coverage.deductible_type_id
            ),
            "deductibleValue": float(
                coverage.deductible_value
            ),
            "coverageCustomDescription": (
                coverage.coverage_custom_description.strip()
            ),
        }
        
    @classmethod
    def _payment_type(
        cls,
        payment_type: ChubbQuotePaymentTypeRequest,
    ) -> dict[str, Any]:
        if not isinstance(payment_type, ChubbQuotePaymentTypeRequest):
            raise ValueError(
                "Cada payment_type debe ser "
                "ChubbQuotePaymentTypeRequest."
            )

        cls._require_positive_int(
            payment_type.payment_type_id,
            "payment_type_id",
        )

        return {
            "paymentTypeId": payment_type.payment_type_id,
        }

    @classmethod
    def _discount(
        cls,
        discount: ChubbQuoteDiscountRequest,
    ) -> dict[str, Any]:
        if not isinstance(discount, ChubbQuoteDiscountRequest):
            raise ValueError(
                "Cada discount debe ser ChubbQuoteDiscountRequest."
            )

        cls._require_positive_int(
            discount.discount_type_id,
            "discount_type_id",
        )
        cls._require_non_empty_string(
            discount.discount_tag,
            "discount_tag",
        )
        cls._require_finite_number(
            discount.discount_percentage,
            "discount_percentage",
        )

        if discount.discount_percentage < 0:
            raise ValueError(
                "discount_percentage no puede ser negativo."
            )

        return {
            "discountTypeId": discount.discount_type_id,
            "discountTag": discount.discount_tag.strip(),
            "discountPercentage": float(
                discount.discount_percentage
            ),
        }

    @classmethod
    def _vehicle(
        cls,
        vehicle: ChubbQuoteVehicleRequest,
    ) -> dict[str, Any]:
        if not isinstance(vehicle, ChubbQuoteVehicleRequest):
            raise ValueError(
                "vehicle debe ser ChubbQuoteVehicleRequest."
            )

        cls._require_non_empty_string(
            vehicle.vehicle_key,
            "vehicle_key",
        )
        cls._require_positive_int(
            vehicle.insured_amount_type_id,
            "insured_amount_type_id",
        )
        cls._require_positive_int(
            vehicle.deductible_type_id,
            "deductible_type_id",
        )
        cls._require_positive_int(vehicle.year, "year")
        cls._require_positive_int(
            vehicle.country_subdivision_id,
            "country_subdivision_id",
        )
        cls._require_positive_int(
            vehicle.municipality_id,
            "municipality_id",
        )
        cls._require_positive_int(vehicle.use_id, "use_id")
        cls._require_bool(vehicle.garage_use, "garage_use")
        cls._require_bool(vehicle.nadasc, "nadasc")
        cls._require_non_empty_string(
            vehicle.reference,
            "vehicle.reference",
        )
        cls._require_string(vehicle.plate, "plate")
        cls._require_non_negative_int(vehicle.age, "age")
        cls._require_positive_int(vehicle.gender_id, "gender_id")

        if not isinstance(vehicle.driver, ChubbQuoteDriverRequest):
            raise ValueError(
                "vehicle.driver debe ser ChubbQuoteDriverRequest."
            )

        return {
            "vehicleKey": vehicle.vehicle_key.strip(),
            "insuredAmountTypeId": vehicle.insured_amount_type_id,
            "deductibleTypeId": vehicle.deductible_type_id,
            "year": vehicle.year,
            "countrySubdivisionId": (
                vehicle.country_subdivision_id
            ),
            "municipalityId": vehicle.municipality_id,
            "useId": vehicle.use_id,
            "garageUse": vehicle.garage_use,
            "nadasc": vehicle.nadasc,
            "reference": vehicle.reference.strip(),
            "plate": vehicle.plate.strip(),
            "age": vehicle.age,
            "genderId": vehicle.gender_id,
            "driver": cls._driver(vehicle.driver),
        }

    @classmethod
    def _driver(
        cls,
        driver: ChubbQuoteDriverRequest,
    ) -> dict[str, Any]:
        if not isinstance(driver, ChubbQuoteDriverRequest):
            raise ValueError(
                "driver debe ser ChubbQuoteDriverRequest."
            )

        cls._require_non_negative_int(driver.tran_id, "tran_id")
        cls._require_non_negative_int(driver.person_id, "person_id")
        cls._require_non_negative_int(
            driver.address_id,
            "address_id",
        )

        return {
            "tranId": driver.tran_id,
            "personId": driver.person_id,
            "addressId": driver.address_id,
        }


    @classmethod
    def _validate_create_quote_request(
        cls,
        request: ChubbCreateQuoteRequest,
    ) -> None:
        cls._require_positive_int(request.product_id, "product_id")
        cls._require_positive_int(
            request.business_profile_id,
            "business_profile_id",
        )
        cls._require_non_empty_string(request.agent_id, "agent_id")
        cls._require_non_negative_int(
            request.conduit_id,
            "conduit_id",
        )
        cls._require_positive_int(
            request.grouping_id,
            "grouping_id",
        )
        cls._require_positive_int(request.rate_id, "rate_id")
        cls._require_date(
            request.effective_date,
            "effective_date",
        )
        cls._require_date(
            request.expiration_date,
            "expiration_date",
        )
        cls._require_positive_int(
            request.calculation_type_id,
            "calculation_type_id",
        )
        cls._require_positive_int(
            request.currency_id,
            "currency_id",
        )
        cls._require_non_empty_string(
            request.reference,
            "reference",
        )
        cls._require_non_empty_string(
            request.prospect_name,
            "prospect_name",
        )

        if request.expiration_date <= request.effective_date:
            raise ValueError(
                "expiration_date debe ser posterior a effective_date."
            )

        if not isinstance(request.payment_types, tuple):
            raise ValueError("payment_types debe ser una tupla.")

        if not request.payment_types:
            raise ValueError(
                "payment_types debe contener al menos un elemento."
            )

        if not isinstance(request.items, tuple):
            raise ValueError("items debe ser una tupla.")

        if not request.items:
            raise ValueError(
                "items debe contener al menos un riesgo."
            )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    
    @staticmethod
    def _require_positive_int(value: Any, field_name: str) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            )

    @staticmethod
    def _require_non_negative_int(
        value: Any,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero mayor o igual a cero."
            )

    @staticmethod
    def _require_bool(value: Any, field_name: str) -> None:
        if not isinstance(value, bool):
            raise ValueError(
                f"{field_name} debe ser booleano."
            )

    @staticmethod
    def _require_date(value: Any, field_name: str) -> None:
        if not isinstance(value, date):
            raise ValueError(
                f"{field_name} debe ser datetime.date."
            )

    @staticmethod
    def _require_string(value: Any, field_name: str) -> None:
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} debe ser una cadena."
            )

    @classmethod
    def _require_non_empty_string(
        cls,
        value: Any,
        field_name: str,
    ) -> None:
        cls._require_string(value, field_name)

        if not value.strip():
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

    @staticmethod
    def _require_finite_number(
        value: Any,
        field_name: str,
    ) -> None:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise ValueError(
                f"{field_name} debe ser numérico."
            )

        if not math.isfinite(float(value)):
            raise ValueError(
                f"{field_name} debe ser un número finito."
            )

    @classmethod
    def _require_non_negative_number(
        cls,
        value: Any,
        field_name: str,
    ) -> None:
        cls._require_finite_number(value, field_name)

        if value < 0:
            raise ValueError(
                f"{field_name} no puede ser negativo."
            )


class ChubbQuoteResponseMapper:
    """
    Valida y transforma la respuesta de Create Quote al contrato interno.

    Por ahora se modela el resumen principal de la cotización y se conserva
    la respuesta completa en raw_response.
    """

    @classmethod
    def create_quote(
        cls,
        payload: Mapping[str, Any],
    ) -> ChubbCreateQuoteResult:
        root = cls._require_mapping(payload, "response")

        success = root.get("isSuccess")

        if not isinstance(success, bool):
            raise ValueError(
                "La respuesta de Chubb no contiene un isSuccess válido."
            )

        if not success:
            messages = root.get("messages") or []

            details = []

            for item in messages:
                if not isinstance(item, dict):
                    continue

                message = str(
                    item.get("message", "")
                ).strip()

                if message:
                    details.append(message)

            detail = "; ".join(details)

            raise ValueError(
                detail or "Chubb rechazó la cotización."
            )

        response_data = cls._require_mapping(
            root.get("responseData"),
            "responseData",
        )

        discounts_payload = cls._require_list(
            response_data.get("discounts"),
            "responseData.discounts",
        )

        discounts = tuple(
            cls._response_discount(discount, index)
            for index, discount in enumerate(discounts_payload)
        )

        items_payload = cls._require_list(
            response_data.get("items"),
            "responseData.items",
        )

        items = tuple(
            cls._response_item(item, index)
            for index, item in enumerate(items_payload)
        )

        return ChubbCreateQuoteResult(
            quote_id=cls._positive_int(
                response_data.get("quoteId"),
                "responseData.quoteId",
            ),
            quote_version_id=cls._positive_int(
                response_data.get("quoteVersionId"),
                "responseData.quoteVersionId",
            ),
            base_net_premium=cls._number(
                response_data.get("baseNetPremium"),
                "responseData.baseNetPremium",
            ),
            base_net_premium_without_discount=cls._number(
                response_data.get(
                    "baseNetPremiumWithoutDiscount"
                ),
                "responseData.baseNetPremiumWithoutDiscount",
            ),
            discounts=discounts,
            surcharge_percentage=cls._nullable_number(
                response_data.get("surchargePercentage"),
                "responseData.surchargePercentage",
            ),
            surcharge_amount=cls._number(
                response_data.get("surchargeAmount"),
                "responseData.surchargeAmount",
            ),
            fee_amount=cls._number(
                response_data.get("feeAmount"),
                "responseData.feeAmount",
            ),
            tax_percentage=cls._nullable_number(
                response_data.get("taxPercentage"),
                "responseData.taxPercentage",
            ),
            tax_amount=cls._number(
                response_data.get("taxAmount"),
                "responseData.taxAmount",
            ),
            total_premium_amount=cls._number(
                response_data.get("totalPremiumAmount"),
                "responseData.totalPremiumAmount",
            ),
            commission_percentage=cls._nullable_number(
                response_data.get("commissionPorcentage"),
                "responseData.commissionPorcentage",
            ),
            commission_amount=cls._nullable_number(
                response_data.get("commissionAmount"),
                "responseData.commissionAmount",
            ),
            surcharge_commission_amount=cls._nullable_number(
                response_data.get("surchargeCommissionAmount"),
                "responseData.surchargeCommissionAmount",
            ),
            items=items,
            raw_response=dict(root),
        )

    @classmethod
    def _response_item(
        cls,
        payload: Any,
        index: int,
    ) -> ChubbQuoteItemResult:
        field_prefix = f"responseData.items[{index}]"
        item = cls._require_mapping(payload, field_prefix)

        vehicle = cls._require_mapping(
            item.get("vehicle"),
            f"{field_prefix}.vehicle",
        )

        packages_payload = cls._require_list(
            item.get("packages"),
            f"{field_prefix}.packages",
        )

        packages = tuple(
            cls._response_package(
                package,
                item_index=index,
                package_index=package_index,
            )
            for package_index, package in enumerate(packages_payload)
        )

        return ChubbQuoteItemResult(
            risk_id=cls._non_negative_int(
                item.get("riskId"),
                f"{field_prefix}.riskId",
            ),
            risk_number=cls._positive_int(
                item.get("riskNumber"),
                f"{field_prefix}.riskNumber",
            ),
            vehicle_key=cls._non_empty_string(
                vehicle.get("vehicleKey"),
                f"{field_prefix}.vehicle.vehicleKey",
            ),
            packages=packages,
        )

    @classmethod
    def _response_package(
        cls,
        payload: Any,
        *,
        item_index: int,
        package_index: int,
    ) -> ChubbQuotePackageResult:
        field_prefix = (
            f"responseData.items[{item_index}]"
            f".packages[{package_index}]"
        )
        package = cls._require_mapping(payload, field_prefix)

        coverages_payload = cls._require_list(
            package.get("coverages"),
            f"{field_prefix}.coverages",
        )

        coverages = tuple(
            cls._response_coverage(
                coverage,
                item_index=item_index,
                package_index=package_index,
                coverage_index=coverage_index,
            )
            for coverage_index, coverage in enumerate(
                coverages_payload
            )
        )

        return ChubbQuotePackageResult(
            package_id=cls._positive_int(
                package.get("packageId"),
                f"{field_prefix}.packageId",
            ),
            description=cls._nullable_string(
                package.get("description"),
                f"{field_prefix}.description",
            ),
            total_premium=cls._number(
                package.get("totalPremiumAmount"),
                f"{field_prefix}.totalPremiumAmount",
            ),
            selected=cls._boolean(
                package.get("selected"),
                f"{field_prefix}.selected",
            ),
            coverages=coverages,
        )


    @classmethod
    def _response_coverage(
        cls,
        payload: Any,
        *,
        item_index: int,
        package_index: int,
        coverage_index: int,
    ) -> ChubbQuoteCoverageResult:
        field_prefix = (
            f"responseData.items[{item_index}]"
            f".packages[{package_index}]"
            f".coverages[{coverage_index}]"
        )
        coverage = cls._require_mapping(payload, field_prefix)

        return ChubbQuoteCoverageResult(
            coverage_id=cls._positive_int(
                coverage.get("coverageId"),
                f"{field_prefix}.coverageId",
            ),
            description=cls._non_empty_string(
                coverage.get("coverageName"),
                f"{field_prefix}.coverageName",
            ),
            custom_name=cls._nullable_string(
                coverage.get("coverageCustomName"),
                f"{field_prefix}.coverageCustomName",
                empty_as_none=True,
            ),
            insured_amount=cls._nullable_number(
                coverage.get("insuranceAmount"),
                f"{field_prefix}.insuranceAmount",
            ),
            premium=cls._number(
                coverage.get("totalPremiumAmount"),
                f"{field_prefix}.totalPremiumAmount",
            ),
            deductible_type_id=cls._nullable_positive_int(
                coverage.get("deductibleTypeId"),
                f"{field_prefix}.deductibleTypeId",
            ),
            deductible_value=cls._nullable_number(
                coverage.get("deductibleValue"),
                f"{field_prefix}.deductibleValue",
            ),
            selected=cls._boolean(
                coverage.get("selected"),
                f"{field_prefix}.selected",
            ),
        )

    @classmethod
    def _response_discount(
        cls,
        payload: Any,
        index: int,
    ) -> ChubbQuoteDiscountResult:
        field_prefix = f"responseData.discounts[{index}]"
        discount = cls._require_mapping(payload, field_prefix)

        return ChubbQuoteDiscountResult(
            discount_type_id=cls._positive_int(
                discount.get("discountTypeId"),
                f"{field_prefix}.discountTypeId",
            ),
            discount_tag=cls._non_empty_string(
                discount.get("discountTag"),
                f"{field_prefix}.discountTag",
            ),
            discount_percentage=cls._number(
                discount.get("discountPercentage"),
                f"{field_prefix}.discountPercentage",
            ),
            discount_amount=cls._number(
                discount.get("discountAmount"),
                f"{field_prefix}.discountAmount",
            ),
        )

    # ------------------------------------------------------------------
    # Response validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _boolean(
        value: Any,
        field_name: str,
    ) -> bool:
        if not isinstance(value, bool):
            raise ValueError(
                f"{field_name} debe ser booleano."
            )

        return value

    @classmethod
    def _nullable_positive_int(
        cls,
        value: Any,
        field_name: str,
    ) -> int | None:
        if value is None:
            return None

        return cls._positive_int(value, field_name)

    @staticmethod
    def _nullable_string(
        value: Any,
        field_name: str,
        *,
        empty_as_none: bool = False,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} debe ser una cadena o null."
            )

        normalized = value.strip()

        if not normalized:
            if empty_as_none:
                return None

            return ""

        return normalized
    
    @staticmethod
    def _require_mapping(
        value: Any,
        field_name: str,
    ) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError(
                f"{field_name} debe ser un objeto JSON."
            )

        return value

    @staticmethod
    def _require_list(
        value: Any,
        field_name: str,
    ) -> list[Any]:
        if not isinstance(value, list):
            raise ValueError(
                f"{field_name} debe ser una lista."
            )

        return value

    @staticmethod
    def _positive_int(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero mayor que cero."
            )

        return value

    @staticmethod
    def _number(
        value: Any,
        field_name: str,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise ValueError(
                f"{field_name} debe ser numérico."
            )

        result = float(value)

        if not math.isfinite(result):
            raise ValueError(
                f"{field_name} debe ser un número finito."
            )

        return result

    @classmethod
    def _nullable_number(
        cls,
        value: Any,
        field_name: str,
    ) -> float | None:
        if value is None:
            return None

        return cls._number(value, field_name)

    @staticmethod
    def _non_empty_string(
        value: Any,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} debe ser una cadena."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

        return normalized

    @staticmethod
    def _non_negative_int(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{field_name} debe ser un entero "
                "mayor o igual a cero."
            )

        return value