from datetime import date, timedelta
from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandError

from cotizador.models import Cotizacion
from integrations.broker.broker import InsuranceBroker
from integrations.broker.mappers.quote_request_mapper import BrokerQuoteRequestMapper
from integrations.broker.mappers.quote_result_mapper import BrokerQuoteResultMapper
from integrations.providers.insurance.chubb.provider import ChubbProvider
from integrations.providers.insurance.chubb.services.quote_service import ChubbQuoteService


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
    help = "Prueba flujo completo mock: Cotizacion -> Broker -> Chubb Mock -> CotizacionItem"

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

        request = BrokerQuoteRequestMapper.from_cotizacion(cotizacion)

        if not request.vehiculo.anio:
            request.vehiculo.anio = 2024

        if not request.vehiculo.codigo_postal and not request.cliente.codigo_postal:
            request.vehiculo.codigo_postal = "45040"

        if not request.vigencia_desde:
            request.vigencia_desde = date.today()

        if not request.vigencia_hasta:
            request.vigencia_hasta = date.today() + timedelta(days=365)

        fake_service = ChubbQuoteService(
            client=FakeChubbApiClient(),
        )

        provider = ChubbProvider(provider_config=provider_config)
        provider.quote_service = fake_service

        result = provider.quote_auto(request)

        items = BrokerQuoteResultMapper.save_to_cotizacion(
            cotizacion=cotizacion,
            result=result,
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== BROKER QUOTE MOCK FULL TEST ==="))
        self.stdout.write(f"Cotización ID : {cotizacion.id}")
        self.stdout.write(f"Folio         : {getattr(cotizacion, 'folio', '')}")
        self.stdout.write(f"OK            : {result.ok}")
        self.stdout.write(f"Opciones      : {len(result.options)}")
        self.stdout.write(f"Errores       : {len(result.errors)}")
        self.stdout.write(f"Items guardados: {len(items)}")

        for item in items:
            self.stdout.write(
                f"- {item.aseguradora.nombre} | "
                f"{item.producto.nombre_producto} | "
                f"{item.paquete_nombre} | "
                f"Prima Total: {item.prima_total}"
            )

        if result.errors:
            self.stdout.write("")
            self.stdout.write("Errores:")
            for error in result.errors:
                self.stdout.write(str(error))
