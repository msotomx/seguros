from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = "Prueba el catálogo Packages de Chubb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--grouping-id",
            required=True,
            type=int,
            help="GroupingId de Chubb.",
        )

        parser.add_argument(
            "--business-profile",
            required=False,
            help="BusinessProfileName de Chubb.",
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
        business_profile = options.get("business_profile")
        ambiente = options["ambiente"]
        ramo = options["ramo"]

        client = ChubbCatalogClient(
            ambiente=ambiente,
            ramo=ramo,
        )

        packages = client.packages(
            grouping_id=grouping_id,
            business_profile_name=business_profile,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(packages)} paquete(s).\n"
            )
        )

        for package in packages:
            self.stdout.write(
                f"PackageId={package.package_id}"
            )
            self.stdout.write(
                f"Nombre={package.name}"
            )
            self.stdout.write(
                f"Descripción={package.description}"
            )
            self.stdout.write("")
