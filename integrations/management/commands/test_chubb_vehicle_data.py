from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = "Prueba el catálogo Vehicle Data de Chubb."

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            required=True,
            help="BusinessProfileName de Chubb.",
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
            "--vehicle-year",
            required=True,
            type=int,
            help="Año del vehículo.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help=(
                "Número máximo de vehículos a mostrar. "
                "El valor predeterminado es 20."
            ),
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
        limit = options["limit"]

        if limit < 0:
            raise CommandError(
                "--limit debe ser mayor o igual a cero."
            )

        try:
            client = ChubbCatalogClient(
                ambiente=options["ambiente"],
                ramo=options["ramo"],
            )

            vehicles = client.vehicle_data(
                business_profile_name=options[
                    "business_profile"
                ],
                grouping_id=options["grouping_id"],
                rate_id=options["rate_id"],
                vehicle_year=options["vehicle_year"],
            )

        except Exception as exc:
            raise CommandError(
                f"No fue posible consultar Vehicle Data: {exc}"
            ) from exc

        total = len(vehicles)
        shown = min(limit, total)

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {total} vehículo(s)."
            )
        )

        self.stdout.write(
            f"Mostrando {shown} vehículo(s).\n"
        )

        for vehicle in vehicles[:limit]:
            self.stdout.write(
                f"VehicleId={vehicle.vehicle_id}"
            )
            self.stdout.write(
                f"VehicleKey={vehicle.vehicle_key}"
            )
            self.stdout.write(
                f"Descripción={vehicle.description}"
            )
            self.stdout.write(
                f"Descripción corta="
                f"{vehicle.short_description}"
            )
            self.stdout.write(
                f"Marca={vehicle.make_description} "
                f"(MakeId={vehicle.make_id})"
            )
            self.stdout.write(
                f"Submarca={vehicle.submake_description} "
                f"(SubMakeId={vehicle.submake_id})"
            )
            self.stdout.write(
                f"Tipo={vehicle.vehicle_type_description} "
                f"(VehicleTypeId={vehicle.vehicle_type_id})"
            )
            self.stdout.write(
                f"Pasajeros={vehicle.passengers}"
            )
            self.stdout.write(
                f"Tonelaje={vehicle.tonnage}"
            )
            self.stdout.write(
                f"CMST={vehicle.cmst}"
            )
            self.stdout.write(
                f"MTC={vehicle.mtc}"
            )
            self.stdout.write(
                f"Activo={vehicle.active}"
            )
            self.stdout.write("")

        if total > shown:
            remaining = total - shown

            self.stdout.write(
                self.style.WARNING(
                    f"No se mostraron {remaining} vehículo(s). "
                    "Usa --limit para ampliar la salida."
                )
            )
