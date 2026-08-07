from django.core.management.base import BaseCommand, CommandError

from integrations.models import AseguradoraConfiguracion
from integrations.providers.chubb.auth import ChubbAuthClient
from integrations.providers.exceptions import ProviderError


class Command(BaseCommand):
    help = "Prueba la autenticación real contra Chubb SIT."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ambiente",
            default=AseguradoraConfiguracion.Ambiente.SIT,
        )

        parser.add_argument(
            "--ramo",
            default=AseguradoraConfiguracion.Ramo.AUTOS,
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Conectando a Chubb..."
            )
        )

        client = ChubbAuthClient(
            provider="CHUBB",
            ambiente=options["ambiente"],
            ramo=options["ramo"],
        )

        try:
            token = client.get_token()

        except ProviderError as exc:
            raise CommandError(str(exc))

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Token obtenido correctamente"
            )
        )

        self.stdout.write(f"Tipo: {token.token_type}")
        self.stdout.write(f"Expira en: {token.expires_in} segundos")

        if token.resource:
            self.stdout.write(f"Resource: {token.resource}")

        masked = (
            token.access_token[:10]
            + "..."
            + token.access_token[-10:]
        )

        self.stdout.write(f"Token: {masked}")
        