from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = "Prueba el catálogo Vehicle Submakes de Chubb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            required=True,
            help="BusinessProfileName de Chubb.",
        )

        parser.add_argument(
            "--make-id",
            required=True,
            type=int,
            help="MakeId de Chubb.",
        )

        parser.add_argument(
            "--grouping-id",
            required=True,
            type=int,
            help="GroupingId de Chubb.",
        )

        parser.add_argument(
            "--rate-id",
            required=True,
            type=int,
            help="RateId de Chubb.",
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
        client = ChubbCatalogClient(
            ambiente=options["ambiente"],
            ramo=options["ramo"],
        )

        submakes = client.vehicle_submakes(
            business_profile_name=options["business_profile"],
            make_id=options["make_id"],
            grouping_id=options["grouping_id"],
            rate_id=options["rate_id"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(submakes)} submarca(s).\n"
            )
        )

        for submake in submakes:
            self.stdout.write(
                f"SubMakeId={submake.submake_id}"
            )
            self.stdout.write(
                f"Nombre={submake.name}"
            )
            self.stdout.write(
                f"Descripción={submake.description}"
            )
            self.stdout.write("")
