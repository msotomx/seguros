from django.core.management.base import BaseCommand, CommandError

from integrations.models import AseguradoraConfiguracion
from integrations.providers.exceptions import ProviderError
from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)

class Command(BaseCommand):
    help = "Consulta el catálogo real business-profiles de Chubb SIT."

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
        ambiente = options["ambiente"]
        ramo = options["ramo"]

        self.stdout.write(
            f"Consultando Chubb business-profiles "
            f"ambiente={ambiente}, ramo={ramo}..."
        )

        try:
            client = ChubbCatalogClient(
                ambiente=ambiente,
                ramo=ramo,
            )

            profiles = client.business_profiles()

        except ProviderError as exc:
            raise CommandError(
                f"No fue posible consultar el catálogo: {exc}"
            ) from exc

        if not profiles:
            self.stdout.write(
                self.style.WARNING(
                    "Chubb respondió correctamente, "
                    "pero no regresó negocios."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(profiles)} negocio(s)."
            )
        )

        for profile in profiles:
            self.stdout.write(
                " - "
                f"ID={profile.business_profile_id} | "
                f"Nombre={profile.name} | "
                f"Descripción={profile.description}"
            )