from django.core.management.base import BaseCommand, CommandError

from integrations.configuration.exceptions import (
    InvalidProviderSetting,
    ProviderConfigurationNotFound,
)
from integrations.configuration.services import ProviderConfigurationService
from integrations.models import AseguradoraConfiguracion


class Command(BaseCommand):
    help = "Prueba la carga de configuración de un Insurance Provider"

    def add_arguments(self, parser):
        parser.add_argument(
            "provider",
            type=str,
            help="Código del Provider, por ejemplo CHUBB",
        )
        parser.add_argument(
            "--ambiente",
            type=str,
            default=AseguradoraConfiguracion.Ambiente.SIT,
            choices=AseguradoraConfiguracion.Ambiente.values,
        )
        parser.add_argument(
            "--ramo",
            type=str,
            default=AseguradoraConfiguracion.Ramo.AUTOS,
            choices=AseguradoraConfiguracion.Ramo.values,
        )

    def handle(self, *args, **options):
        provider = options["provider"].upper()
        ambiente = options["ambiente"]
        ramo = options["ramo"]

        try:
            config = ProviderConfigurationService.get_active(
                provider=provider,
                ambiente=ambiente,
                ramo=ramo,
            )
        except ProviderConfigurationNotFound as exc:
            raise CommandError(str(exc)) from exc
        except InvalidProviderSetting as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("=== PROVIDER CONFIGURATION TEST ===")
        )

        self.stdout.write(f"ID           : {config.id}")
        self.stdout.write(f"Provider     : {config.provider}")
        self.stdout.write(f"Nombre       : {config.nombre}")
        self.stdout.write(f"Ambiente     : {config.ambiente}")
        self.stdout.write(f"Ramo         : {config.ramo}")
        self.stdout.write(f"Activo       : {config.activo}")
        self.stdout.write(f"Prioridad    : {config.prioridad}")
        self.stdout.write(f"Aseguradora  : {config.aseguradora_id or '-'}")
        self.stdout.write(f"Base URL     : {config.base_url}")
        self.stdout.write(f"Token URL    : {config.token_url}")
        self.stdout.write(f"API version  : {config.api_version}")
        self.stdout.write(f"Timeout      : {config.timeout}")

        self.stdout.write("")
        self.stdout.write("Capacidades:")
        self.stdout.write(f"  Cotización     : {config.supports_quote}")
        self.stdout.write(f"  Emisión        : {config.supports_issue}")
        self.stdout.write(f"  Documentos     : {config.supports_documents}")
        self.stdout.write(f"  Pagos          : {config.supports_payments}")
        self.stdout.write(f"  Endosos        : {config.supports_endorsements}")
        self.stdout.write(f"  Cancelación    : {config.supports_cancellation}")
        self.stdout.write(f"  Renovación     : {config.supports_renewal}")

        self.stdout.write("")
        self.stdout.write("Provider settings:")

        if not config.settings:
            self.stdout.write("  (sin parámetros activos)")
        else:
            for key, value in sorted(config.settings.items()):
                self.stdout.write(
                    f"  {key} = {value!r} "
                    f"({type(value).__name__})"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Configuración cargada correctamente.")
        )
        