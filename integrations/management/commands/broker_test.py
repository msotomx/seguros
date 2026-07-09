from django.core.management.base import BaseCommand

from integrations.broker.broker import InsuranceBroker
from integrations.broker.contracts import (
    BrokerQuoteRequest,
    BrokerCustomerData,
    BrokerVehicleData,
)


class Command(BaseCommand):
    help = "Prueba motor Broker de Switchh"

    def handle(self, *args, **options):

        broker = InsuranceBroker()

        request = BrokerQuoteRequest(
            cotizacion_id=0,
            cliente=BrokerCustomerData(
                tipo_cliente="INDIVIDUAL",
                nombre="Cliente de prueba",
            ),
            vehiculo=BrokerVehicleData(
                marca="Nissan",
                submarca="Versa",
                anio=2024,
            ),
        )

        result = broker.quote_auto(request)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== SWITCHH BROKER ==="))
        self.stdout.write(f"Cotizaciones recibidas : {len(result.options)}")
        self.stdout.write(f"Errores                : {len(result.errors)}")

        if result.errors:
            self.stdout.write("")
            self.stdout.write("Detalle de errores:")

            for error in result.errors:
                self.stdout.write(
                    f"  [{error['provider']}] {error['error']}"
                )
