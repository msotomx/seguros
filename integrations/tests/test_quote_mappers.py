from __future__ import annotations

from copy import deepcopy

from django.test import SimpleTestCase

from dataclasses import replace
from datetime import date

from integrations.providers.chubb.quote_contracts import (
    ChubbCreateQuoteRequest,
    ChubbQuoteCoverageRequest,
    ChubbQuoteDiscountRequest,
    ChubbQuoteDriverRequest,
    ChubbQuoteItemRequest,
    ChubbQuotePackageRequest,
    ChubbQuotePaymentTypeRequest,
    ChubbQuoteVehicleRequest,
)
from integrations.providers.chubb.quote_mappers import (
    ChubbQuoteRequestMapper,
    ChubbQuoteResponseMapper,
)

def _coverage_payload() -> dict:
    return {
        "coverageId": 1,
        "coverageName": "DAÑOS MATERIALES",
        "coverageCustomName": "",
        "selected": True,
        "insuranceAmount": 10000.0,
        "deductibleValue": 4.0,
        "baseNetPremium": 551.55,
        "totalPremiumAmount": 639.798,
    }


def _package_payload() -> dict:
    return {
        "packageId": 1,
        "quoteVersionId": 2061297738,
        "riskId": None,
        "selected": True,
        "baseNetPremium": 551.55,
        "totalPremiumAmount": 639.798,
        "coverages": [
            _coverage_payload(),
        ],
    }


def _item_payload() -> dict:
    return {
        "riskId": 2061426582,
        "riskNumber": 1,
        "totalPremiumAmount": 639.798,
        "vehicle": {
            "vehicleId": 146,
            "vehicleKey": "03070300101",
            "vehicleDescription": "HP2 ENDURO",
        },
        "packages": [
            _package_payload(),
        ],
    }


def _response_payload() -> dict:
    return {
        "isSuccess": True,
        "messages": [],
        "responseData": {
            "quoteId": 2061062766,
            "quoteVersionId": 2061297738,
            "baseNetPremium": 27078.182,
            "baseNetPremiumWithoutDiscount": 27078.182,
            "discounts": [
                {
                    "discountTypeId": 1,
                    "discountTag": "Descuento",
                    "discountPercentage": 0.0,
                    "discountAmount": 0,
                },
                {
                    "discountTypeId": 2,
                    "discountTag": "Bonificación",
                    "discountPercentage": 0.0,
                    "discountAmount": 0,
                },
            ],
            "surchargePercentage": 0.0,
            "surchargeAmount": 0.0,
            "feeAmount": 600.0,
            "taxPercentage": None,
            "taxAmount": 4428.5091,
            "totalPremiumAmount": 32106.6911,
            "commissionPorcentage": None,
            "commissionAmount": None,
            "surchargeCommissionAmount": None,
            "items": [
                _item_payload(),
            ],
        },
    }


class ChubbQuoteResponseMapperTests(SimpleTestCase):
    def test_create_quote_maps_complete_response(self):
        payload = _response_payload()

        result = ChubbQuoteResponseMapper.create_quote(payload)

        self.assertEqual(result.quote_id, 2061062766)
        self.assertEqual(result.quote_version_id, 2061297738)
        self.assertEqual(result.base_net_premium, 27078.182)
        self.assertEqual(
            result.base_net_premium_without_discount,
            27078.182,
        )
        self.assertEqual(result.surcharge_percentage, 0.0)
        self.assertEqual(result.surcharge_amount, 0.0)
        self.assertEqual(result.fee_amount, 600.0)
        self.assertIsNone(result.tax_percentage)
        self.assertEqual(result.tax_amount, 4428.5091)
        self.assertEqual(result.total_premium_amount, 32106.6911)
        self.assertIsNone(result.commission_percentage)
        self.assertIsNone(result.commission_amount)
        self.assertIsNone(result.surcharge_commission_amount)
        self.assertEqual(result.raw_response, payload)

    def test_create_quote_maps_discounts(self):
        result = ChubbQuoteResponseMapper.create_quote(
            _response_payload()
        )

        self.assertEqual(len(result.discounts), 2)

        first_discount = result.discounts[0]

        self.assertEqual(first_discount.discount_type_id, 1)
        self.assertEqual(
            first_discount.discount_tag,
            "Descuento",
        )
        self.assertEqual(
            first_discount.discount_percentage,
            0.0,
        )
        self.assertEqual(first_discount.discount_amount, 0.0)

    def test_create_quote_maps_item(self):
        result = ChubbQuoteResponseMapper.create_quote(
            _response_payload()
        )

        self.assertEqual(len(result.items), 1)

        item = result.items[0]

        self.assertEqual(item.risk_id, 2061426582)
        self.assertEqual(item.risk_number, 1)
        self.assertEqual(item.vehicle_key, "03070300101")
        self.assertEqual(len(item.packages), 1)

    def test_create_quote_maps_package(self):
        result = ChubbQuoteResponseMapper.create_quote(
            _response_payload()
        )

        package = result.items[0].packages[0]

        self.assertEqual(package.package_id, 1)
        self.assertEqual(package.total_premium, 639.798)
        self.assertTrue(package.selected)
        self.assertEqual(len(package.coverages), 1)

    def test_create_quote_maps_coverage(self):
        result = ChubbQuoteResponseMapper.create_quote(
            _response_payload()
        )

        coverage = result.items[0].packages[0].coverages[0]

        self.assertEqual(coverage.coverage_id, 1)
        self.assertEqual(
            coverage.description,
            "DAÑOS MATERIALES",
        )
        self.assertIsNone(coverage.custom_name)
        self.assertEqual(coverage.insured_amount, 10000.0)
        self.assertEqual(coverage.premium, 639.798)
        self.assertIsNone(coverage.deductible_type_id)
        self.assertEqual(coverage.deductible_value, 4.0)
        self.assertTrue(coverage.selected)

    def test_create_quote_maps_non_empty_custom_name(self):
        payload = _response_payload()
        coverage = (
            payload["responseData"]["items"][0]
            ["packages"][0]["coverages"][0]
        )
        coverage["coverageCustomName"] = " GPS Y RADIO "

        result = ChubbQuoteResponseMapper.create_quote(payload)

        mapped_coverage = (
            result.items[0].packages[0].coverages[0]
        )

        self.assertEqual(
            mapped_coverage.custom_name,
            "GPS Y RADIO",
        )

    def test_create_quote_accepts_null_coverage_values(self):
        payload = _response_payload()
        coverage = (
            payload["responseData"]["items"][0]
            ["packages"][0]["coverages"][0]
        )
        coverage["coverageCustomName"] = None
        coverage["insuranceAmount"] = None
        coverage["deductibleValue"] = None
        coverage["deductibleTypeId"] = None

        result = ChubbQuoteResponseMapper.create_quote(payload)

        mapped_coverage = (
            result.items[0].packages[0].coverages[0]
        )

        self.assertIsNone(mapped_coverage.custom_name)
        self.assertIsNone(mapped_coverage.insured_amount)
        self.assertIsNone(mapped_coverage.deductible_value)
        self.assertIsNone(
            mapped_coverage.deductible_type_id
        )

    def test_create_quote_accepts_risk_id_zero(self):
        payload = _response_payload()
        payload["responseData"]["items"][0]["riskId"] = 0

        result = ChubbQuoteResponseMapper.create_quote(payload)

        self.assertEqual(result.items[0].risk_id, 0)

    def test_create_quote_rejects_negative_risk_id(self):
        payload = _response_payload()
        payload["responseData"]["items"][0]["riskId"] = -1

        with self.assertRaisesRegex(
            ValueError,
            r"responseData\.items\[0\]\.riskId",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_risk_number_zero(self):
        payload = _response_payload()
        payload["responseData"]["items"][0]["riskNumber"] = 0

        with self.assertRaisesRegex(
            ValueError,
            r"responseData\.items\[0\]\.riskNumber",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_empty_vehicle_key(self):
        payload = _response_payload()
        payload["responseData"]["items"][0]["vehicle"][
            "vehicleKey"
        ] = "   "

        with self.assertRaisesRegex(
            ValueError,
            r"vehicle\.vehicleKey",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_invalid_package_selected(self):
        payload = _response_payload()
        payload["responseData"]["items"][0]["packages"][0][
            "selected"
        ] = 1

        with self.assertRaisesRegex(
            ValueError,
            r"packages\[0\]\.selected",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_empty_coverage_name(self):
        payload = _response_payload()
        coverage = (
            payload["responseData"]["items"][0]
            ["packages"][0]["coverages"][0]
        )
        coverage["coverageName"] = " "

        with self.assertRaisesRegex(
            ValueError,
            r"coverages\[0\]\.coverageName",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_invalid_coverage_selected(self):
        payload = _response_payload()
        coverage = (
            payload["responseData"]["items"][0]
            ["packages"][0]["coverages"][0]
        )
        coverage["selected"] = "true"

        with self.assertRaisesRegex(
            ValueError,
            r"coverages\[0\]\.selected",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_invalid_total_premium(self):
        payload = _response_payload()
        coverage = (
            payload["responseData"]["items"][0]
            ["packages"][0]["coverages"][0]
        )
        coverage["totalPremiumAmount"] = "639.798"

        with self.assertRaisesRegex(
            ValueError,
            r"coverages\[0\]\.totalPremiumAmount",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_unsuccessful_response(self):
        payload = {
            "isSuccess": False,
            "messages": [
                {
                    "code": "CHUBB.ERROR",
                    "message": "Cotización rechazada",
                }
            ],
            "responseData": None,
        }

        with self.assertRaisesRegex(
            ValueError,
            "Cotización rechazada",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_create_quote_rejects_missing_response_data(self):
        payload = {
            "isSuccess": True,
            "responseData":None,
            "messages": [],
        }

        with self.assertRaisesRegex(
            ValueError,
            "responseData debe ser un objeto JSON",
        ):
            ChubbQuoteResponseMapper.create_quote(payload)

    def test_mapper_does_not_modify_original_payload(self):
        payload = _response_payload()
        original = deepcopy(payload)

        ChubbQuoteResponseMapper.create_quote(payload)

        self.assertEqual(payload, original)

def _driver_request() -> ChubbQuoteDriverRequest:
    return ChubbQuoteDriverRequest(
        tran_id=0,
        person_id=0,
        address_id=0,
    )


def _vehicle_request() -> ChubbQuoteVehicleRequest:
    return ChubbQuoteVehicleRequest(
        vehicle_key=" 03070300101 ",
        insured_amount_type_id=1,
        deductible_type_id=1,
        year=2024,
        country_subdivision_id=1,
        municipality_id=1,
        use_id=1,
        garage_use=True,
        nadasc=False,
        reference=" VEH-001 ",
        plate=" ABC-123 ",
        age=40,
        gender_id=1,
        driver=_driver_request(),
    )


def _coverage_request() -> ChubbQuoteCoverageRequest:
    return ChubbQuoteCoverageRequest(
        coverage_id=9,
        insurance_amount=449950.0,
        deductible_type_id=1,
        deductible_value=0.0,
        coverage_custom_description=" GPS y radio ",
    )


def _package_request() -> ChubbQuotePackageRequest:
    return ChubbQuotePackageRequest(
        package_id=1,
        selected=True,
        coverages=(
            _coverage_request(),
        ),
    )

def _discount_request() -> ChubbQuoteDiscountRequest:
    return ChubbQuoteDiscountRequest(
        discount_type_id=1,
        discount_tag=" Descuento ",
        discount_percentage=10.0,
    )

def _item_request() -> ChubbQuoteItemRequest:
    return ChubbQuoteItemRequest(
        risk_id=0,
        risk_number=1,
        discounts=(
            _discount_request(),
        ),
        vehicle=_vehicle_request(),
        packages=(
            _package_request(),
        ),
    )

def _create_quote_request() -> ChubbCreateQuoteRequest:
    return ChubbCreateQuoteRequest(
        product_id=1,
        business_profile_id=207637,
        agent_id=" AGENTE-01 ",
        conduit_id=0,
        grouping_id=207637,
        rate_id=400,
        effective_date=date(2026, 7, 23),
        expiration_date=date(2027, 7, 23),
        calculation_type_id=1,
        currency_id=1,
        reference=" COT-0001 ",
        prospect_name=" Miguel Soto ",
        payment_types=(
            ChubbQuotePaymentTypeRequest(
                payment_type_id=1,
            ),
        ),
        items=(
            _item_request(),
        ),
    )

class ChubbQuoteRequestMapperTests(SimpleTestCase):

    def test_create_quote_serializes_complete_request(self):
        request = _create_quote_request()

        payload = ChubbQuoteRequestMapper.create_quote(request)

        self.assertEqual(
            payload,
            {
                "productId": 1,
                "businessprofileId": 207637,
                "agentId": "AGENTE-01",
                "conduitId": 0,
                "groupingId": 207637,
                "rateId": 400,
                "effectiveDate": "2026-07-23",
                "expirationDate": "2027-07-23",
                "calculationTypeId": 1,
                "currencyId": 1,
                "reference": "COT-0001",
                "prospectName": "Miguel Soto",
                "paymentTypes": [
                    {
                        "paymentTypeId": 1,
                    }
                ],
                "items": [
                    {
                        "riskId": 0,
                        "riskNumber": 1,
                        "discount": [
                            {
                                "discountTypeId": 1,
                                "discountTag": "Descuento",
                                "discountPercentage": 10.0,
                            }
                        ],
                        "vehicle": {
                            "vehicleKey": "03070300101",
                            "insuredAmountTypeId": 1,
                            "deductibleTypeId": 1,
                            "year": 2024,
                            "countrySubdivisionId": 1,
                            "municipalityId": 1,
                            "useId": 1,
                            "garageUse": True,
                            "nadasc": False,
                            "reference": "VEH-001",
                            "plate": "ABC-123",
                            "age": 40,
                            "genderId": 1,
                            "driver": {
                                "tranId": 0,
                                "personId": 0,
                                "addressId": 0,
                            },
                        },
                        "packages": [
                            {
                                "packageId": 1,
                                "selected": True,
                                "coverages": [
                                    {
                                        "coverageId": 9,
                                        "insuranceAmount": 449950.0,
                                        "deductibleTypeId": 1,
                                        "deductibleValue": 0.0,
                                        "coverageCustomDescription": (
                                            "GPS y radio"
                                        ),
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        )

    def test_create_quote_preserves_exact_chubb_keys(self):
        payload = ChubbQuoteRequestMapper.create_quote(
            _create_quote_request()
        )

        self.assertIn("businessprofileId", payload)
        self.assertNotIn("businessProfileId", payload)

        item = payload["items"][0]

        self.assertIn("discount", item)
        self.assertNotIn("discounts", item)

        coverage = item["packages"][0]["coverages"][0]

        self.assertIn(
            "coverageCustomDescription",
            coverage,
        )
        self.assertNotIn(
            "coverageCustomName",
            coverage,
        )

    def test_create_quote_serializes_dates_as_iso_strings(self):
        payload = ChubbQuoteRequestMapper.create_quote(
            _create_quote_request()
        )

        self.assertEqual(
            payload["effectiveDate"],
            "2026-07-23",
        )
        self.assertEqual(
            payload["expirationDate"],
            "2027-07-23",
        )

    def test_create_quote_trims_string_values(self):
        payload = ChubbQuoteRequestMapper.create_quote(
            _create_quote_request()
        )

        item = payload["items"][0]
        vehicle = item["vehicle"]
        coverage = item["packages"][0]["coverages"][0]

        self.assertEqual(payload["agentId"], "AGENTE-01")
        self.assertEqual(payload["reference"], "COT-0001")
        self.assertEqual(payload["prospectName"], "Miguel Soto")
        self.assertEqual(
            item["discount"][0]["discountTag"],
            "Descuento",
        )
        self.assertEqual(
            vehicle["vehicleKey"],
            "03070300101",
        )
        self.assertEqual(vehicle["reference"], "VEH-001")
        self.assertEqual(vehicle["plate"], "ABC-123")
        self.assertEqual(
            coverage["coverageCustomDescription"],
            "GPS y radio",
        )

    def test_create_quote_accepts_risk_id_zero(self):
        payload = ChubbQuoteRequestMapper.create_quote(
            _create_quote_request()
        )

        self.assertEqual(
            payload["items"][0]["riskId"],
            0,
        )

    def test_create_quote_accepts_zero_driver_ids(self):
        payload = ChubbQuoteRequestMapper.create_quote(
            _create_quote_request()
        )

        driver = payload["items"][0]["vehicle"]["driver"]

        self.assertEqual(
            driver,
            {
                "tranId": 0,
                "personId": 0,
                "addressId": 0,
            },
        )

    def test_create_quote_accepts_empty_discounts_tuple(self):
        item = replace(
            _item_request(),
            discounts=(),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        payload = ChubbQuoteRequestMapper.create_quote(request)

        self.assertEqual(
            payload["items"][0]["discount"],
            [],
        )

    def test_create_quote_accepts_empty_coverages_tuple(self):
        package = replace(
            _package_request(),
            coverages=(),
        )
        item = replace(
            _item_request(),
            packages=(package,),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        payload = ChubbQuoteRequestMapper.create_quote(request)

        self.assertEqual(
            payload["items"][0]["packages"][0]["coverages"],
            [],
        )

    def test_create_quote_rejects_invalid_request_type(self):
        with self.assertRaisesRegex(
            ValueError,
            "request debe ser una instancia",
        ):
            ChubbQuoteRequestMapper.create_quote({})

    def test_create_quote_rejects_empty_agent_id(self):
        request = replace(
            _create_quote_request(),
            agent_id="   ",
        )

        with self.assertRaisesRegex(
            ValueError,
            "agent_id no puede estar vacío",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_expiration_equal_to_effective(self):
        request = replace(
            _create_quote_request(),
            expiration_date=date(2026, 7, 23),
        )

        with self.assertRaisesRegex(
            ValueError,
            "expiration_date debe ser posterior",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_expiration_before_effective(self):
        request = replace(
            _create_quote_request(),
            expiration_date=date(2026, 7, 22),
        )

        with self.assertRaisesRegex(
            ValueError,
            "expiration_date debe ser posterior",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_payment_types_as_list(self):
        request = replace(
            _create_quote_request(),
            payment_types=[
                ChubbQuotePaymentTypeRequest(
                    payment_type_id=1,
                )
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "payment_types debe ser una tupla",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_empty_payment_types(self):
        request = replace(
            _create_quote_request(),
            payment_types=(),
        )

        with self.assertRaisesRegex(
            ValueError,
            "payment_types debe contener al menos",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_items_as_list(self):
        request = replace(
            _create_quote_request(),
            items=[
                _item_request(),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "items debe ser una tupla",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_empty_items(self):
        request = replace(
            _create_quote_request(),
            items=(),
        )

        with self.assertRaisesRegex(
            ValueError,
            "items debe contener al menos",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_negative_risk_id(self):
        item = replace(
            _item_request(),
            risk_id=-1,
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "risk_id debe ser un entero mayor o igual a cero",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_risk_number_zero(self):
        item = replace(
            _item_request(),
            risk_number=0,
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "risk_number debe ser un entero mayor que cero",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_packages_as_list(self):
        item = replace(
            _item_request(),
            packages=[
                _package_request(),
            ],
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "item.packages debe ser una tupla",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_empty_packages(self):
        item = replace(
            _item_request(),
            packages=(),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "Cada item debe contener al menos un paquete",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_invalid_package_selected(self):
        package = replace(
            _package_request(),
            selected=1,
        )
        item = replace(
            _item_request(),
            packages=(package,),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "package.selected debe ser booleano",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_invalid_vehicle_boolean(self):
        vehicle = replace(
            _vehicle_request(),
            garage_use=1,
        )
        item = replace(
            _item_request(),
            vehicle=vehicle,
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "garage_use debe ser booleano",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_negative_vehicle_age(self):
        vehicle = replace(
            _vehicle_request(),
            age=-1,
        )
        item = replace(
            _item_request(),
            vehicle=vehicle,
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "age debe ser un entero mayor o igual a cero",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_negative_discount_percentage(self):
        discount = replace(
            _discount_request(),
            discount_percentage=-0.01,
        )
        item = replace(
            _item_request(),
            discounts=(discount,),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "discount_percentage no puede ser negativo",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_non_finite_discount(self):
        discount = replace(
            _discount_request(),
            discount_percentage=float("nan"),
        )
        item = replace(
            _item_request(),
            discounts=(discount,),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "discount_percentage debe ser un número finito",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_negative_insurance_amount(self):
        coverage = replace(
            _coverage_request(),
            insurance_amount=-1,
        )
        package = replace(
            _package_request(),
            coverages=(coverage,),
        )
        item = replace(
            _item_request(),
            packages=(package,),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "insurance_amount no puede ser negativo",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_negative_deductible_value(self):
        coverage = replace(
            _coverage_request(),
            deductible_value=-1,
        )
        package = replace(
            _package_request(),
            coverages=(coverage,),
        )
        item = replace(
            _item_request(),
            packages=(package,),
        )
        request = replace(
            _create_quote_request(),
            items=(item,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "deductible_value no puede ser negativo",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_rejects_invalid_payment_type_id(self):
        request = replace(
            _create_quote_request(),
            payment_types=(
                ChubbQuotePaymentTypeRequest(
                    payment_type_id=0,
                ),
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "payment_type_id debe ser un entero mayor que cero",
        ):
            ChubbQuoteRequestMapper.create_quote(request)

    def test_create_quote_does_not_modify_request(self):
        request = _create_quote_request()

        ChubbQuoteRequestMapper.create_quote(request)

        self.assertEqual(
            request.agent_id,
            " AGENTE-01 ",
        )
        self.assertEqual(
            request.reference,
            " COT-0001 ",
        )
        self.assertEqual(
            request.prospect_name,
            " Miguel Soto ",
        )
        self.assertEqual(
            request.items[0].vehicle.vehicle_key,
            " 03070300101 ",
        )
