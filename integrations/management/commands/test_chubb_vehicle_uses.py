from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = (
        "Prueba el catálogo de Vehicle Uses de Chubb."
    )

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
            "--grouping-id",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--country-subdivision-id",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--rate-id",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--use-id",
            type=int,
            required=True,
        )

    def handle(self, *args, **options):
        client = ChubbCatalogClient(
            ambiente=options["ambiente"],
            ramo=options["ramo"],
        )

        uses = client.vehicle_uses(
            grouping_id=options["grouping_id"],
            country_subdivision_id=options[
                "country_subdivision_id"
            ],
            rate_id=options["rate_id"],
            use_id=options["use_id"],
        )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(
            "CHUBB - Vehicle Uses"
        )
        self.stdout.write("=" * 60)

        self.stdout.write("")
        self.stdout.write("Parámetros")
        self.stdout.write("-" * 10)
        self.stdout.write(
            f"GroupingId:            {options['grouping_id']}"
        )
        self.stdout.write(
            "CountrySubdivisionId:  "
            f"{options['country_subdivision_id']}"
        )
        self.stdout.write(
            f"RateId:                {options['rate_id']}"
        )
        self.stdout.write(
            f"UseId:                 {options['use_id']}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"Total de relaciones: {len(uses)}"
        )

        for item in uses:
            self.stdout.write("")
            self.stdout.write("-" * 60)
            self.stdout.write(
                f"ServiceId : {item.service_id}"
            )
            self.stdout.write(
                f"Servicio  : {item.service_description}"
            )
            self.stdout.write(
                f"UseId     : {item.use_id}"
            )
            self.stdout.write(
                f"Uso        : {item.use_description}"
            )

        self.stdout.write("")
        self.stdout.write("=" * 60)
