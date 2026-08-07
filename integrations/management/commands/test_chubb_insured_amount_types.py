from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = (
        "Prueba el catálogo de Insured Amount Types de Chubb."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            required=True,
            help="BusinessProfileName de Chubb.",
        )

        parser.add_argument(
            "--rate-id",
            required=True,
            type=int,
            help="RateId de Chubb.",
        )

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
        business_profile = options["business_profile"]
        rate_id = options["rate_id"]
        grouping_id = options["grouping_id"]
        ambiente = options["ambiente"]
        ramo = options["ramo"]

        client = ChubbCatalogClient(
            ambiente=ambiente,
            ramo=ramo,
        )

        insured_amount_types = client.insured_amount_types(
            business_profile_name=business_profile,
            rate_id=rate_id,
            grouping_id=grouping_id,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(insured_amount_types)} tipo(s) de suma asegurada.\n"
            )
        )

        for insured_amount_type in insured_amount_types:
            self.stdout.write(
                f"InsuredAmountTypeId={insured_amount_type.insured_amount_type_id}"
            )
            self.stdout.write(
                f"Nombre={insured_amount_type.name}"
            )
            self.stdout.write(
                f"Descripción={insured_amount_type.description}"
            )
            self.stdout.write(
                f"Default={insured_amount_type.is_default}"
            )
            self.stdout.write(
                f"VehicleClassId={insured_amount_type.vehicle_class_id}"
            )
            self.stdout.write(
                f"VehicleConditionId={insured_amount_type.vehicle_condition_id}"
            )
            self.stdout.write("")
