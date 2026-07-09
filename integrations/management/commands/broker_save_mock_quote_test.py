from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from cotizador.models import Cotizacion
from integrations.broker.contracts import (
    BrokerQuoteResult,
    BrokerQuoteOption,
)
from integrations.broker.mappers.quote_result_mapper import BrokerQuoteResultMapper


class Command(BaseCommand):
    help = "Guarda un BrokerQuoteResult mock como CotizacionItem(s)"

    def add_arguments(self, parser):
        parser.add_argument("cotizacion_id", type=int)

    def handle(self, *args, **options):
        cotizacion_id = options["cotizacion_id"]

        try:
            cotizacion = Cotizacion.objects.get(id=cotizacion_id)
        except Cotizacion.DoesNotExist:
            raise CommandError(f"No existe Cotizacion con id={cotizacion_id}")

        result = BrokerQuoteResult(
            request=None,
            options=[
                BrokerQuoteOption(
                    provider="CHUBB",
                    provider_quote_id="12345:1",
                    product_name="Chubb Auto",
                    package_name="Paquete 101",
                    prima_neta=Decimal("10000.00"),
                    derechos=Decimal("500.00"),
                    recargos=Decimal("0.00"),
                    iva=Decimal("1680.00"),
                    prima_total=Decimal("12180.00"),
                    payment_type="",
                    raw_response={
                        "quoteId": 12345,
                        "quoteVersionId": 1,
                        "mock": True,
                    },
                )
            ],
        )

        items = BrokerQuoteResultMapper.save_to_cotizacion(
            cotizacion=cotizacion,
            result=result,
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== BROKER SAVE MOCK QUOTE TEST ==="))
        self.stdout.write(f"Cotización ID : {cotizacion.id}")
        self.stdout.write(f"Items creados/actualizados: {len(items)}")

        for item in items:
            self.stdout.write(
                f"- {item.aseguradora.nombre} | "
                f"{item.producto.nombre_producto} | "
                f"{item.paquete_nombre} | "
                f"Prima Total: {item.prima_total}"
            )
