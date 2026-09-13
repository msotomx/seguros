from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)
from integrations.providers.chubb.suburb_sync_service import (
    ChubbSuburbSyncService,
)


class Command(BaseCommand):
    help = (
        "Prueba el catálogo Suburbs de Chubb y opcionalmente "
        "sincroniza sus valores con el catálogo interno."
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
            "--zip-code",
            required=True,
        )
        parser.add_argument(
            "--sync",
            action="store_true",
        )

    def handle(self, *args, **options):
        client = ChubbCatalogClient(
            ambiente=options["ambiente"],
            ramo=options["ramo"],
        )

        zip_code = options["zip_code"]

        suburbs = client.suburbs(
            zip_code=zip_code,
        )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("CHUBB - Suburbs")
        self.stdout.write("=" * 60)

        self.stdout.write("")
        self.stdout.write(f"ZipCode: {zip_code}")
        self.stdout.write(
            f"Total de colonias: {len(suburbs)}"
        )

        for item in suburbs:
            self.stdout.write("")
            self.stdout.write("-" * 60)
            self.stdout.write(
                f"SuburbId             : {item.suburb_id}"
            )
            self.stdout.write(
                f"Colonia              : {item.name}"
            )
            self.stdout.write(
                "CountrySubdivisionId : "
                f"{item.country_subdivision_id}"
            )
            self.stdout.write(
                "MunicipalityId        : "
                f"{item.municipality_id}"
            )
            self.stdout.write(
                f"PopulationId          : {item.population_id}"
            )

        if not options["sync"]:
            return

        mappings = ChubbSuburbSyncService.sync(
            provider_id=client.configuration.id,
            zip_code=zip_code,
            catalog_client=client,
        )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(
            f"Mappings sincronizados: {len(mappings)}"
        )
        self.stdout.write("=" * 60)

        for mapping in mappings:
            self.stdout.write(
                f"{mapping.catalog_item.code} -> "
                f"{mapping.external_code}"
            )
