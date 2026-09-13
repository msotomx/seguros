# Este comando sincroniza el catalogo de vehiculos de Chubb y los carga en el ERP
# 
# python manage.py sync_chubb_vehicle_catalog \
#   --ambiente sit \
#   --ramo autos \
#   --vehicle-year 2024
# Esto únicamente debe validar que existe la configuración.
#
# Después, conscientemente:
#
# python manage.py sync_chubb_vehicle_catalog \
#   --ambiente sit \
#   --ramo autos \
#   --vehicle-year 2024 \
#   --send

from __future__ import annotations

import traceback

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)
from integrations.providers.chubb.vehicle_catalog_sync_service import (
    ChubbVehicleCatalogSyncService,
)


class Command(BaseCommand):
    help = (
        "Sincroniza el catálogo de vehículos de Chubb "
        "con el catálogo interno del ERP."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--ambiente",
            required=True,
            help="Ambiente configurado del provider.",
        )

        parser.add_argument(
            "--ramo",
            required=True,
            help="Ramo configurado del provider.",
        )

        parser.add_argument(
            "--vehicle-year",
            type=int,
            required=True,
            help="Año de los vehículos a sincronizar.",
        )

        parser.add_argument(
            "--send",
            action="store_true",
            help=(
                "Consulta realmente el catálogo del provider "
                "y persiste los mapeos. "
                "Sin este flag sólo valida la configuración."
            ),
        )

    def handle(self, *args, **options) -> None:
        ambiente = options["ambiente"].strip()
        ramo = options["ramo"].strip()
        vehicle_year = options["vehicle_year"]

        if not ambiente:
            raise CommandError(
                "ambiente no puede estar vacío."
            )

        if not ramo:
            raise CommandError(
                "ramo no puede estar vacío."
            )

        if (
            isinstance(vehicle_year, bool)
            or not isinstance(vehicle_year, int)
            or vehicle_year < 1950
            or vehicle_year > 2100
        ):
            raise CommandError(
                "vehicle-year está fuera del rango permitido."
            )

        try:
            catalog_client = ChubbCatalogClient(
                ambiente=ambiente,
                ramo=ramo,
            )
        except Exception as exc:
            raise CommandError(
                f"No fue posible resolver la configuración: {exc}"
            ) from exc

        configuration = catalog_client.configuration

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n=== SYNC CATÁLOGO VEHÍCULOS ==="
            )
        )

        self.stdout.write(
            f"Provider config : {configuration.id}"
        )
        self.stdout.write(
            f"Ambiente        : {ambiente}"
        )
        self.stdout.write(
            f"Ramo            : {ramo}"
        )
        self.stdout.write(
            f"Año             : {vehicle_year}"
        )

        if not options["send"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "No se consultó el catálogo del provider."
                )
            )
            self.stdout.write(
                "La configuración activa fue encontrada "
                "correctamente."
            )

            self.stdout.write("")
            self.stdout.write(
                "Para ejecutar realmente:"
            )

            self.stdout.write(
                self.style.HTTP_INFO(
                    "python manage.py "
                    "sync_chubb_vehicle_catalog "
                    f"--ambiente {ambiente} "
                    f"--ramo {ramo} "
                    f"--vehicle-year {vehicle_year} "
                    "--send"
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Consultando y sincronizando vehículos..."
            )
        )

        try:
            mappings = (
                ChubbVehicleCatalogSyncService.sync(
                    provider_id=configuration.id,
                    vehicle_year=vehicle_year,
                    catalog_client=catalog_client,
                )
            )
        except Exception as exc:
            self.stderr.write("")
            self.stderr.write(
                self.style.ERROR(
                    "La sincronización terminó con error."
                )
            )

            self.stderr.write(
                traceback.format_exc()
            )

            raise CommandError(
                f"Sync de vehículos falló: {exc}"
            ) from exc

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo sincronizado correctamente."
            )
        )

        self.stdout.write(
            f"Mapeos activos procesados: {len(mappings)}"
        )
