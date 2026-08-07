from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = "Prueba el catálogo Vehicle Years de Chubb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            required=True,
            help="BusinessProfileName de Chubb.",
        )

        parser.add_argument(
            "--vehicle-type-id",
            required=True,
            type=int,
            help="VehicleTypeId de Chubb.",
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
            help="Ramo de Chubb.",
        )

    def handle(self, *args, **options):
        try:
            client = ChubbCatalogClient(
                ambiente=options["ambiente"],
                ramo=options["ramo"],
            )

            years = client.vehicle_years(
                business_profile_name=options[
                    "business_profile"
                ],
                vehicle_type_id=options[
                    "vehicle_type_id"
                ],
                grouping_id=options["grouping_id"],
                rate_id=options["rate_id"],
            )

        except Exception as exc:
            raise CommandError(
                f"No fue posible consultar Vehicle Years: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(years)} año(s).\n"
            )
        )

        for vehicle_year in years:
            self.stdout.write(
                f"Year={vehicle_year.year}"
            )
            self.stdout.write(
                f"Nombre={vehicle_year.name}"
            )
            self.stdout.write(
                f"Descripción={vehicle_year.description}"
            )
            self.stdout.write("")
