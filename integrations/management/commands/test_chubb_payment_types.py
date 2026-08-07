from django.core.management.base import BaseCommand

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)


class Command(BaseCommand):
    help = (
        "Prueba el catálogo de Payment Types de Chubb."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile-id",
            required=True,
            type=int,
            help="BusinessProfileId de Chubb.",
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
        business_profile_id = options["business_profile_id"]
        grouping_id = options["grouping_id"]
        ambiente = options["ambiente"]
        ramo = options["ramo"]

        client = ChubbCatalogClient(
            ambiente=ambiente,
            ramo=ramo,
        )

        payment_types = client.payment_types(
            business_profile_id=business_profile_id,
            grouping_id=grouping_id,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Chubb devolvió {len(payment_types)} tipo(s) de pago.\n"
            )
        )

        for payment_type in payment_types:
            self.stdout.write(
                f"PaymentTypeId={payment_type.payment_type_id}"
            )
            self.stdout.write(
                f"Nombre={payment_type.name}"
            )
            self.stdout.write(
                f"Descripción={payment_type.description}"
            )
            self.stdout.write("")
            