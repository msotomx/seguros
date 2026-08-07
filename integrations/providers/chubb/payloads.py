from __future__ import annotations

from datetime import date

from integrations.providers.chubb.contracts import (
    ChubbQuoteContext,
)
from integrations.providers.contracts import (
    QuoteRequest,
)
from integrations.providers.exceptions import (
    ProviderQuoteError,
)


class ChubbQuotePayloadBuilder:
    """
    Convierte QuoteRequest + ChubbQuoteContext al body requerido
    por POST /quote.

    No consulta base de datos.
    No consulta catálogos.
    No realiza HTTP.
    """

    @classmethod
    def build(
        cls,
        *,
        request: QuoteRequest,
        context: ChubbQuoteContext,
    ) -> dict:
        cls._validate_request(request)
        cls._validate_context(context)

        vehicle = {
            "vehicleKey": context.vehicle_key,
            "vehicleId": context.vehicle_id,
            "insuredAmountTypeId": (
                context.insured_amount_type_id
            ),
            "deductibleTypeId": context.deductible_type_id,
            "year": request.vehicle.year,
            "countrySubdivisionId": (
                context.country_subdivision_id
            ),
            "municipalityId": context.municipality_id,
            "zipCode": cls._postal_code_as_int(
                request.vehicle.postal_code
            ),
            "useId": context.vehicle_use_id,
            "garageUse": context.garage_use,
            "nadasc": context.nadasc,
            "reference": context.reference,
        }

        cls._add_optional_vehicle_fields(
            vehicle=vehicle,
            request=request,
        )

        age = cls._calculate_age(
            birth_date=request.insured.birth_date,
            reference_date=request.start_date,
        )

        if age is not None:
            vehicle["age"] = age

        payload = {
            "quoteId": 0,
            "quoteVersionId": 0,
            "quoteType": 0,
            "productId": context.product_id,
            "businessprofileId": (
                context.business_profile_id
            ),
            "agentId": context.agent_id,
            "conduitId": context.conduit_id,
            "groupingId": context.grouping_id,
            "rateId": context.rate_id,
            "effectiveDate": request.start_date.isoformat(),
            "expirationDate": request.end_date.isoformat(),
            "calculationTypeId": (
                context.calculation_type_id
            ),
            "currencyId": context.currency_id,
            "reference": context.reference,
            "prospectName": context.prospect_name,
            "paymentTypes": [
                {
                    "paymentTypeId": context.payment_type_id,
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
                            "discountPercentage": float(
                                context.discount_percentage
                            ),
                        },
                        {
                            "discountTypeId": 2,
                            "discountTag": "Bonificación",
                            "discountPercentage": float(
                                context.bonus_percentage
                            ),
                        },
                    ],
                    "vehicle": vehicle,
                    "packages": [
                        {
                            "packageId": context.package_id,
                            "selected": True,
                            "coverages": [],
                        }
                    ],
                }
            ],
        }

        return payload

    @staticmethod
    def build_headers(
        *,
        context: ChubbQuoteContext,
    ) -> dict[str, str]:
        """
        Headers específicos adicionales para POST /quote.

        Authorization y ApiVersion son agregados por
        ChubbHttpClient.
        """

        return {
            "CB-SourceApplication": str(
                context.source_application
            ),
        }

    @staticmethod
    def _add_optional_vehicle_fields(
        *,
        vehicle: dict,
        request: QuoteRequest,
    ) -> None:
        if request.vehicle.serial_number:
            vehicle["vin"] = request.vehicle.serial_number

        if request.vehicle.plates:
            vehicle["plate"] = request.vehicle.plates

    @staticmethod
    def _calculate_age(
        *,
        birth_date: date | None,
        reference_date: date,
    ) -> int | None:
        if birth_date is None:
            return None

        if birth_date > reference_date:
            raise ProviderQuoteError(
                "La fecha de nacimiento no puede ser posterior "
                "al inicio de vigencia."
            )

        age = reference_date.year - birth_date.year

        if (
            reference_date.month,
            reference_date.day,
        ) < (
            birth_date.month,
            birth_date.day,
        ):
            age -= 1

        return age

    @staticmethod
    def _postal_code_as_int(value: str) -> int:
        normalized = str(value).strip()

        if not normalized.isdigit():
            raise ProviderQuoteError(
                "El código postal debe contener únicamente números."
            )

        return int(normalized)

    @staticmethod
    def _validate_request(
        request: QuoteRequest,
    ) -> None:
        if not isinstance(request, QuoteRequest):
            raise TypeError(
                "request debe ser una instancia de QuoteRequest."
            )

        if request.end_date <= request.start_date:
            raise ProviderQuoteError(
                "La fecha final debe ser posterior "
                "a la fecha inicial."
            )

        if request.vehicle.year <= 0:
            raise ProviderQuoteError(
                "El año del vehículo no es válido."
            )

    @staticmethod
    def _validate_context(
        context: ChubbQuoteContext,
    ) -> None:
        if not isinstance(context, ChubbQuoteContext):
            raise TypeError(
                "context debe ser una instancia "
                "de ChubbQuoteContext."
            )

        required_positive_ids = {
            "product_id": context.product_id,
            "business_profile_id": (
                context.business_profile_id
            ),
            "agent_id": context.agent_id,
            "grouping_id": context.grouping_id,
            "rate_id": context.rate_id,
            "calculation_type_id": (
                context.calculation_type_id
            ),
            "currency_id": context.currency_id,
            "payment_type_id": context.payment_type_id,
            "vehicle_id": context.vehicle_id,
            "insured_amount_type_id": (
                context.insured_amount_type_id
            ),
            "deductible_type_id": (
                context.deductible_type_id
            ),
            "country_subdivision_id": (
                context.country_subdivision_id
            ),
            "municipality_id": context.municipality_id,
            "vehicle_use_id": context.vehicle_use_id,
            "package_id": context.package_id,
        }

        missing = [
            name
            for name, value in required_positive_ids.items()
            if not isinstance(value, int) or value <= 0
        ]

        if missing:
            raise ProviderQuoteError(
                "El contexto de Chubb contiene identificadores "
                f"inválidos: {', '.join(missing)}."
            )

        if (
            not isinstance(context.conduit_id, int)
            or context.conduit_id < 0
        ):
            raise ProviderQuoteError(
                "conduit_id debe ser cero o un entero positivo."
            )

        if not context.vehicle_key.strip():
            raise ProviderQuoteError(
                "vehicle_key no puede estar vacío."
            )
        