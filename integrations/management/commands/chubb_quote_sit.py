from __future__ import annotations

import json
import traceback
from dataclasses import asdict
from datetime import timedelta
from typing import Any

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone

from integrations.providers.chubb.quote_client import (
    ChubbQuoteClient,
)
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
)


class Command(BaseCommand):
    help = (
        "Ejecuta una prueba SIT de Create Quote contra Chubb. "
        "Sin --send solamente construye y muestra el payload."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--send",
            action="store_true",
            help="Envía realmente la cotización a Chubb SIT.",
        )
        parser.add_argument(
            "--show-raw-response",
            action="store_true",
            help="Muestra raw_response completo.",
        )

        parser.add_argument(
            "--vehicle-key",
            default="01140300301",
            help="Clave del vehículo obtenida del catálogo de Chubb.",
        )
        parser.add_argument(
            "--vehicle-year",
            type=int,
            default=2015,
        )
        parser.add_argument(
            "--package-id",
            type=int,
            default=2,
        )
        parser.add_argument(
            "--payment-type-id",
            type=int,
            default=12,
        )
        parser.add_argument(
            "--municipality-id",
            type=int,
            default=42,
        )
        parser.add_argument(
            "--country-subdivision-id",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--prospect-name",
            default="PRUEBA SIT SWITCHH",
        )
        parser.add_argument(
            "--reference",
            default="SWITCHH-SIT-QUOTE",
        )

    def handle(self, *args, **options) -> None:
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n=== CHUBB CREATE QUOTE — SIT ==="
            )
        )

        try:
            request = self._build_request(options)
            payload = ChubbQuoteRequestMapper.create_quote(request)
        except ValueError as exc:
            raise CommandError(
                f"El request local no es válido: {exc}"
            ) from exc

        self._print_payload(payload)

        if not options["send"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "No se realizó ninguna llamada a Chubb."
                )
            )
            self.stdout.write(
                "Para enviar el request:"
            )
            self.stdout.write(
                self.style.HTTP_INFO(
                    "python manage.py chubb_quote_sit --send"
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Enviando cotización al ambiente SIT de Chubb..."
            )
        )

        try:
            quote_client = ChubbQuoteClient(
                ambiente="SIT",
                ramo="AUTOS",
            )

            result = quote_client.create_quote(request)

        except Exception as exc:
            self.stderr.write("")
            self.stderr.write(
                self.style.ERROR(
                    "La prueba SIT terminó con error."
                )
            )
            self.stderr.write(traceback.format_exc())

            raise CommandError(
                f"Create Quote falló: {exc}"
            ) from exc

        self._print_result(
            result,
            show_raw_response=options["show_raw_response"],
        )

    def _build_request(
        self,
        options: dict[str, Any],
    ) -> ChubbCreateQuoteRequest:
        today = timezone.localdate()

        return ChubbCreateQuoteRequest(
            product_id=1,
            business_profile_id=7190,
            agent_id="91840",
            conduit_id=0,
            grouping_id=353991,
            rate_id=453,
            effective_date=today,
            expiration_date=today + timedelta(days=365),
            calculation_type_id=2,
            currency_id=1,
            reference=options["reference"],
            prospect_name=options["prospect_name"],
            payment_types=(
                ChubbQuotePaymentTypeRequest(
                    payment_type_id=options["payment_type_id"],
                ),
            ),
            items=(
                ChubbQuoteItemRequest(
                    risk_id=0,
                    risk_number=1,
                    discounts=(
                        ChubbQuoteDiscountRequest(
                            discount_type_id=1,
                            discount_tag="Descuento",
                            discount_percentage=0.0,
                        ),
                        ChubbQuoteDiscountRequest(
                            discount_type_id=2,
                            discount_tag="Bonificacion",
                            discount_percentage=0.0,
                        ),
                    ),
                    vehicle=ChubbQuoteVehicleRequest(
                        vehicle_key=options["vehicle_key"],
                        insured_amount_type_id=1,
                        deductible_type_id=1,
                        year=options["vehicle_year"],
                        country_subdivision_id=(
                            options["country_subdivision_id"]
                        ),
                        municipality_id=options["municipality_id"],
                        use_id=1,
                        garage_use=False,
                        nadasc=False,
                        reference="VEHICULO SIT SWITCHH",
                        plate="SIT001",
                        age=40,
                        gender_id=1,
                        driver=ChubbQuoteDriverRequest(
                            tran_id=0,
                            person_id=0,
                            address_id=0,
                        ),
                    ),
                    packages=(
                        ChubbQuotePackageRequest(
                            package_id=options["package_id"],
                            selected=True,
                            coverages=(
                                ChubbQuoteCoverageRequest(
                                    coverage_id=2,
                                    insurance_amount=0.0,
                                    deductible_type_id=1,
                                    deductible_value=15.0,
                                    coverage_custom_description="",
                                ),
                                ChubbQuoteCoverageRequest(
                                    coverage_id=45,
                                    insurance_amount=0.0,
                                    deductible_type_id=1,
                                    deductible_value=15.0,
                                    coverage_custom_description="",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

    def _print_payload(
        self,
        payload: dict[str, Any],
    ) -> None:
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "JSON que se enviará a Chubb:"
            )
        )
        self.stdout.write(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
        )

    def _print_result(
        self,
        result,
        *,
        show_raw_response: bool,
    ) -> None:
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Create Quote ejecutado correctamente."
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(
                "Resultado normalizado:"
            )
        )

        result_data = asdict(result)
        raw_response = result_data.pop(
            "raw_response",
            None,
        )

        self.stdout.write(
            json.dumps(
                result_data,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

        if show_raw_response:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_LABEL(
                    "Respuesta original de Chubb:"
                )
            )
            self.stdout.write(
                json.dumps(
                    raw_response,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )
