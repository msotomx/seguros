from types import SimpleNamespace

from django.core.management.base import BaseCommand
from datetime import date, timedelta

from integrations.broker.broker import InsuranceBroker
from integrations.broker.contracts import (
    BrokerQuoteRequest,
    BrokerCustomerData,
    BrokerVehicleData,
)
from integrations.providers.insurance.chubb.services.quote_service import ChubbQuoteService
from integrations.providers.insurance.chubb.provider import ChubbProvider


class FakeChubbApiClient:
    def post_quote(self, payload):
        return {
            "quoteId": 12345,
            "quoteVersionId": 1,
            "baseNetPremiumWithoutDiscount": "10000.00",
            "feeAmount": "500.00",
            "taxAmount": "1680.00",
            "surchargeAmount": "0.00",
            "totalPremiumAmount": "12180.00",
            "items": [
                {
                    "riskId": 1,
                    "riskNumber": 1,
                    "packages": [
                        {
                            "packageId": 101,
                            "selected": True,
                            "totalPremiumAmount": "12180.00",
                        }
                    ],
                }
            ],
        }


class Command(BaseCommand):
    help = "Prueba la cadena de cotización Chubb sin llamar a la API real"

    def handle(self, *args, **options):
        provider_config = SimpleNamespace(
            product_id=1,
            businessprofile_id=1,
            agent_id=1,
            conduit_id=1,
            grouping_id=1,
            rate_id=1,
            calculation_type_id=1,
            currency_id=1,
            payment_type_id=1,
            vehicle_key="TEST-VEHICLE-KEY",
            vehicle_id=1,
            insured_amount_type_id=1,
            deductible_type_id=0,
            country_subdivision_id=14,
            municipality_id=39,
            use_id=1,
            package_id=101,
            discount_type_id=1,
            discount_percentage=0,
        )

        request = BrokerQuoteRequest(
            cotizacion_id=999,
            cliente=BrokerCustomerData(
                tipo_cliente="INDIVIDUAL",
                nombre="Cliente Prueba",
                email="cliente@test.com",
                telefono="3312345678",
                codigo_postal="45040",
            ),
            vehiculo=BrokerVehicleData(
                tipo_uso="PARTICULAR",
                anio=2024,
                marca="Nissan",
                submarca="Versa",
                version="Sense",
                placas="",
                vin="",
                codigo_postal="45040",
            ),
            vigencia_desde=date.today(),
            vigencia_hasta=date.today() + timedelta(days=365),
        )

        fake_service = ChubbQuoteService(
            client=FakeChubbApiClient(),
        )

        provider = ChubbProvider(provider_config=provider_config)
        provider.quote_service = fake_service

        result = provider.quote_auto(request)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== CHUBB QUOTE CHAIN TEST ==="))
        self.stdout.write(f"OK: {result.ok}")
        self.stdout.write(f"Opciones: {len(result.options)}")
        self.stdout.write(f"Errores: {len(result.errors)}")

        if result.options:
            option = result.options[0]
            self.stdout.write("")
            self.stdout.write("Primera opción:")
            self.stdout.write(f"  Provider Quote ID: {option.provider_quote_id}")
            self.stdout.write(f"  Producto         : {option.product_name}")
            self.stdout.write(f"  Paquete          : {option.package_name}")
            self.stdout.write(f"  Prima Total      : {option.prima_total}")

        if result.errors:
            self.stdout.write("")
            self.stdout.write("Errores:")
            for error in result.errors:
                self.stdout.write(str(error))
