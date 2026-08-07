from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)
from integrations.providers.exceptions import (
    ProviderError,
)


class Command(BaseCommand):
    help = "Consulta el catálogo real de agentes de Chubb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ambiente",
            default="SIT",
        )
        parser.add_argument(
            "--ramo",
            default="AUTOS",
        )
        parser.add_argument(
            "--business-profile-name",
            default="BASE_TOM",
        )

    def handle(self, *args, **options):
        ambiente = options["ambiente"]
        ramo = options["ramo"]
        business_profile_name = options[
            "business_profile_name"
        ]

        self.stdout.write(
            "Consultando Chubb agents "
            f"ambiente={ambiente}, "
            f"ramo={ramo}, "
            f"business_profile={business_profile_name}..."
        )

        try:
            client = ChubbCatalogClient(
                ambiente=ambiente,
                ramo=ramo,
            )

            agents = client.agents(
                business_profile_name=(
                    business_profile_name
                ),
            )

        except ProviderError as exc:
            raise CommandError(
                "No fue posible consultar el catálogo "
                f"de agentes: {exc}"
            ) from exc

        if not agents:
            self.stdout.write(
                self.style.WARNING(
                    "Chubb respondió correctamente, "
                    "pero no regresó agentes."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(agents)} agente(s)."
            )
        )

        for agent in agents:
            self.stdout.write(
                " - "
                f"AgentOptionId={agent.agent_option_id} | "
                f"Nombre={agent.name} | "
                f"Descripción={agent.description}"
            )
            