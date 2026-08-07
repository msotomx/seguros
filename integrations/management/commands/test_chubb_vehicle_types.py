from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = "Prueba el catálogo Vehicle Types de Chubb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            required=True,
        )
        parser.add_argument(
            "--submake-id",
            required=True,
            type=int,
        )
        parser.add_argument(
            "--grouping-id",
            required=True,
            type=int,
        )
        parser.add_argument(
            "--rate-id",
            required=True,
            type=int,
        )
        parser.add_argument(
            "--ambiente",
            required=True,
            choices=["sit", "prod"],
        )
        parser.add_argument(
            "--ramo",
            required=True,
            choices=["autos"],
        )

    def handle(self, *args, **options):
        client = ChubbCatalogClient(
            ambiente=options["ambiente"],
            ramo=options["ramo"],
        )

        vehicle_types = client.vehicle_types(
            business_profile_name=options[
                "business_profile"
            ],
            submake_id=options["submake_id"],
            grouping_id=options["grouping_id"],
            rate_id=options["rate_id"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió "
                f"{len(vehicle_types)} tipo(s) de vehículo.\n"
            )
        )

        for vehicle_type in vehicle_types:
            self.stdout.write(
                f"VehicleTypeId="
                f"{vehicle_type.vehicle_type_id}"
            )
            self.stdout.write(
                f"Nombre={vehicle_type.name}"
            )
            self.stdout.write(
                f"Descripción={vehicle_type.description}"
            )
            self.stdout.write("")
