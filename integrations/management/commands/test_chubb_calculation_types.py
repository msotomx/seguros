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

        parser.add_argument(
            "--business-profile",
            default="BASE_TOM",
            dest="business_profile",
        )

        parser.add_argument(
            "--agent-option-id",
            type=int,
            default=91840,
            dest="agent_option_id",
        )

    def handle(self, *args, **options):
        ambiente = options["ambiente"]
        ramo = options["ramo"]
        business_profile = options["business_profile"]
        agent_option_id = options["agent_option_id"]

        self.stdout.write(
            "Consultando Chubb calculation-types "
            f"ambiente={ambiente}, "
            f"ramo={ramo}, "
            f"business_profile={business_profile}, "
            f"agent_option_id={agent_option_id}..."
        )

        try:
            client = ChubbCatalogClient(
                ambiente=ambiente,
                ramo=ramo,
            )

            calculation_types = client.calculation_types(
                business_profile_name=business_profile,
                agent_option_id=agent_option_id,
            )

        except ProviderError as exc:
            raise CommandError(
                f"No fue posible consultar el catálogo: {exc}"
            ) from exc

        if not calculation_types:
            self.stdout.write(
                self.style.WARNING(
                    "Chubb respondió correctamente, "
                    "pero no regresó tipos de cálculo."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Chubb devolvió "
                f"{len(calculation_types)} "
                "tipo(s) de cálculo."
            )
        )

        for item in calculation_types:
            self.stdout.write(
                " - "
                f"CalculationTypeId={item.calculation_type_id} | "
                f"Nombre={item.name} | "
                f"Descripción={item.description}"
            )
