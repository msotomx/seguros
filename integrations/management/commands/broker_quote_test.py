# Para probar el broker con una cotizacion real
# 
from django.core.management.base import BaseCommand, CommandError

from cotizador.models import Cotizacion
from integrations.broker.broker import InsuranceBroker
from integrations.broker.mappers.quote_request_mapper import BrokerQuoteRequestMapper


class Command(BaseCommand):
    help = "Prueba el Motor Broker usando una cotización real"

    def add_arguments(self, parser):
        parser.add_argument("cotizacion_id", type=int)

    def handle(self, *args, **options):
        cotizacion_id = options["cotizacion_id"]

        try:
            cotizacion = Cotizacion.objects.select_related(
                "cliente",
                "vehiculo",
            ).get(id=cotizacion_id)
        except Cotizacion.DoesNotExist:
            raise CommandError(f"No existe Cotizacion con id={cotizacion_id}")

        request = BrokerQuoteRequestMapper.from_cotizacion(cotizacion)

        broker = InsuranceBroker()
        result = broker.quote_auto(request)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== SWITCHH BROKER QUOTE TEST ==="))
        self.stdout.write(f"Cotización ID     : {cotizacion_id}")
        self.stdout.write(f"Cliente           : {request.cliente.nombre}")
        self.stdout.write(f"Vehículo          : {request.vehiculo.marca} {request.vehiculo.submarca} {request.vehiculo.anio}")
        self.stdout.write(f"Opciones recibidas: {len(result.options)}")
        self.stdout.write(f"Errores           : {len(result.errors)}")

        if result.errors:
            self.stdout.write("")
            self.stdout.write("Detalle de errores:")
            for error in result.errors:
                self.stdout.write(f"  [{error['provider']}] {error['error']}")
