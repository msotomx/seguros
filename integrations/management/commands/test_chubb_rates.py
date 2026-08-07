from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = (
        "Prueba el catálogo de Rates de Chubb."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--grouping-id",
            required=True,
            type=int,
            help="GroupingId de Chubb.",
        )

        parser.add_argument(
            "--ambiente",
            required=True,
            choices=["sit", "prod"],
            help="Ambiente de Chubb.",
        )

        parser.add_argument(
            "--ramo",
            required=True,
            choices=["autos"],
            help="Ramo de negocio.",
        )

    def handle(self, *args, **options):
        grouping_id = options["grouping_id"]
        ambiente = options["ambiente"]
        ramo = options["ramo"]

        client = ChubbCatalogClient(
            ambiente=ambiente,
            ramo=ramo,
        )

        rates = client.rates(
            grouping_id=grouping_id,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(rates)} tarifa(s).\n"
            )
        )

        for rate in rates:
            self.stdout.write(
                f"RateId={rate.rate_id}"
            )
            self.stdout.write(
                f"Nombre={rate.name}"
            )
            self.stdout.write(
                f"Descripción={rate.description}"
            )
            self.stdout.write(
                f"RateTypeId={rate.rate_type_id}"
            )
            self.stdout.write("")
