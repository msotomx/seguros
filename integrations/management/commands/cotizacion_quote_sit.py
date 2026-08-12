from __future__ import annotations

import json
import traceback

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from cotizador.models import Cotizacion
from cotizador.services.cotizacion_quote_service import (
    CotizacionQuoteService,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.quote_provider_builder import (
    ChubbQuoteProviderBuilder,
)


class Command(BaseCommand):
    help = (
        "Cotiza una Cotizacion real del ERP contra Chubb SIT "
        "y persiste el resultado."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--cotizacion-id",
            type=int,
            required=True,
            help="ID de la Cotizacion del ERP.",
        )

        parser.add_argument(
            "--package-code",
            default="AMPLIA",
            help=(
                "Código canónico del paquete en el ERP. "
                "Ejemplo: AMPLIA."
            ),
        )

        parser.add_argument(
            "--garage",
            action="store_true",
            help="Indica que el vehículo tiene uso de garage.",
        )

        parser.add_argument(
            "--send",
            action="store_true",
            help=(
                "Ejecuta realmente la cotización contra Chubb SIT. "
                "Sin este flag sólo valida la preparación."
            ),
        )

        parser.add_argument(
            "--show-response",
            action="store_true",
            help="Muestra la respuesta persistida completa.",
        )

    def handle(self, *args, **options) -> None:
        cotizacion_id = options["cotizacion_id"]
        package_code = options["package_code"]
        garage = options["garage"]

        try:
            cotizacion = (
                Cotizacion.objects
                .select_related(
                    "cliente",
                    "vehiculo",
                    "vehiculo__catalogo",
                )
                .get(pk=cotizacion_id)
            )
        except Cotizacion.DoesNotExist as exc:
            raise CommandError(
                f"No existe Cotizacion id={cotizacion_id}."
            ) from exc

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n=== COTIZACION ERP → CHUBB SIT ==="
            )
        )

        self.stdout.write(
            f"Cotizacion : {cotizacion.id}"
        )
        self.stdout.write(
            f"Folio      : {cotizacion.folio}"
        )
        self.stdout.write(
            f"Cliente    : {cotizacion.cliente.nombre_mostrar}"
        )
        self.stdout.write(
            f"Paquete    : {package_code}"
        )
        self.stdout.write(
            f"Garage     : {garage}"
        )

        try:
            configuration = (
                ProviderConfigurationService.get_active(
                    provider="CHUBB",
                    ambiente="SIT",
                    ramo="AUTOS",
                )
            )

            provider = ChubbQuoteProviderBuilder().build(
                ambiente="SIT",
                ramo="AUTOS",
            )

        except Exception as exc:
            raise CommandError(
                f"No fue posible preparar Chubb: {exc}"
            ) from exc

        if not options["send"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "No se realizó llamada a Chubb."
                )
            )
            self.stdout.write(
                "Configuración y Cotizacion encontradas correctamente."
            )
            self.stdout.write("")
            self.stdout.write(
                "Para enviar realmente:"
            )
            self.stdout.write(
                self.style.HTTP_INFO(
                    "python manage.py cotizacion_quote_sit "
                    f"--cotizacion-id {cotizacion.id} "
                    f"--package-code {package_code} "
                    "--send"
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Enviando cotización real a Chubb SIT..."
            )
        )

        try:
            registro = CotizacionQuoteService.quote_one(
                cotizacion=cotizacion,
                configuration=configuration,
                provider=provider,
                package_code=package_code,
                garage=garage,
            )

        except Exception as exc:
            self.stderr.write("")
            self.stderr.write(
                self.style.ERROR(
                    "La cotización ERP → Chubb terminó con error."
                )
            )
            self.stderr.write(
                traceback.format_exc()
            )

            raise CommandError(
                f"Cotización falló: {exc}"
            ) from exc

        self.stdout.write("")

        if not registro.success:
            self.stderr.write(
                self.style.ERROR(
                    "Chubb respondió con un intento fallido."
                )
            )
            self.stderr.write(
                f"Tipo    : {registro.error_type}"
            )
            self.stderr.write(
                f"Mensaje : {registro.error_message}"
            )
            self.stderr.write(
                f"Retry   : {registro.error_retryable}"
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Cotización ejecutada y persistida correctamente."
            )
        )

        self.stdout.write("")
        self.stdout.write(
            f"CotizacionProveedor ID : {registro.id}"
        )
        self.stdout.write(
            f"Provider               : {registro.provider_code}"
        )
        self.stdout.write(
            f"Quote ID               : {registro.provider_quote_id}"
        )
        self.stdout.write(
            "Quote Version ID       : "
            f"{registro.provider_quote_version_id}"
        )
        self.stdout.write(
            f"Prima neta             : {registro.net_premium}"
        )
        self.stdout.write(
            f"Gastos                  : {registro.fees}"
        )
        self.stdout.write(
            f"Impuestos               : {registro.taxes}"
        )
        self.stdout.write(
            f"Prima total             : {registro.total_premium}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"Riesgos                 : {registro.riesgos.count()}"
        )
        self.stdout.write(
            f"Opciones                : {registro.opciones.count()}"
        )

        for riesgo in registro.riesgos.all():
            self.stdout.write("")
            self.stdout.write(
                f"Risk ID                 : "
                f"{riesgo.provider_risk_id}"
            )
            self.stdout.write(
                f"Vehicle Key             : {riesgo.vehicle_key}"
            )

            for opcion in riesgo.opciones.all():
                self.stdout.write(
                    f"  Package ID            : "
                    f"{opcion.provider_package_id}"
                )
                self.stdout.write(
                    f"  Paquete               : {opcion.name}"
                )
                self.stdout.write(
                    f"  Prima paquete         : "
                    f"{opcion.total_premium}"
                )

                for cobertura in opcion.coberturas.all():
                    self.stdout.write(
                        f"    Coverage {cobertura.code}: "
                        f"{cobertura.name} "
                        f"Prima={cobertura.premium}"
                    )

        if options["show_response"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_LABEL(
                    "Response JSON persistido:"
                )
            )
            self.stdout.write(
                json.dumps(
                    registro.response_json,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )
