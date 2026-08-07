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
    help = (
        "Consulta el catálogo de agrupaciones "
        "de Chubb en el ambiente configurado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            default="BASE_TOM",
            help=(
                "Nombre del Business Profile. "
                "Valor predeterminado: BASE_TOM."
            ),
        )

        parser.add_argument(
            "--agent-option-id",
            type=int,
            default=91840,
            help=(
                "Identificador de la opción de agente. "
                "Valor predeterminado: 91840."
            ),
        )

        parser.add_argument(
            "--ambiente",
            default="sit",
            help=(
                "Ambiente de Chubb. "
                "Valor predeterminado: sit."
            ),
        )

        parser.add_argument(
            "--ramo",
            default="autos",
            help=(
                "Ramo configurado para Chubb. "
                "Valor predeterminado: autos."
            ),
        )

    def handle(self, *args, **options):
        business_profile = (
            options["business_profile"].strip()
        )
        agent_option_id = options["agent_option_id"]
        ambiente = options["ambiente"].strip()
        ramo = options["ramo"].strip()

        if not business_profile:
            raise CommandError(
                "--business-profile no puede estar vacío."
            )

        if agent_option_id <= 0:
            raise CommandError(
                "--agent-option-id debe ser un entero positivo."
            )

        if not ambiente:
            raise CommandError(
                "--ambiente no puede estar vacío."
            )

        if not ramo:
            raise CommandError(
                "--ramo no puede estar vacío."
            )

        try:
            client = ChubbCatalogClient(
                ambiente=ambiente,
                ramo=ramo,
            )

            groupings = client.groupings(
                business_profile_name=business_profile,
                agent_option_id=agent_option_id,
            )

        except ProviderError as exc:
            raise CommandError(
                "No fue posible consultar Groupings: "
                f"{exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Chubb devolvió "
                f"{len(groupings)} agrupación(es)."
            )
        )

        if not groupings:
            self.stdout.write(
                self.style.WARNING(
                    "El catálogo de agrupaciones está vacío."
                )
            )
            return

        for grouping in groupings:
            self.stdout.write("")
            self.stdout.write(
                f"GroupingId={grouping.grouping_id}"
            )
            self.stdout.write(
                f"Nombre={grouping.name}"
            )
            self.stdout.write(
                f"Descripción={grouping.description}"
            )
            