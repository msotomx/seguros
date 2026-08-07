from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from integrations.providers.chubb.catalog_client import (
    ChubbCatalogClient,
)
from integrations.providers.exceptions import (
    ProviderError,
)


class Command(BaseCommand):
    help = (
        "Consulta el catálogo de monedas de Chubb "
        "en el ambiente configurado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-profile",
            default="BASE_TOM",
            help=(
                "Nombre del Business Profile. "
                "Valor predeterminado: BASE_TOM."
            ),
        )

        parser.add_argument(
            "--ambiente",
            default="sit",
            help=(
                "Ambiente de Chubb. "
                "Valor predeterminado: sit."
            ),
        )

        parser.add_argument(
            "--ramo",
            default="autos",
            help=(
                "Ramo configurado para Chubb. "
                "Valor predeterminado: autos."
            ),
        )

    def handle(self, *args, **options):
        ambiente = options["ambiente"].strip()
        ramo = options["ramo"].strip()
        business_profile = (
            options["business_profile"].strip()
        )

        if not business_profile:
            raise CommandError(
                "--business-profile no puede estar vacío."
            )

        client = ChubbCatalogClient(
                ambiente=ambiente,
                ramo=ramo,
            )


        try:
            currencies = client.currencies(
                business_profile_name=business_profile,
            )
        except ProviderError as exc:
            raise CommandError(
                f"No fue posible consultar Currencies: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Chubb devolvió "
                f"{len(currencies)} moneda(s)."
            )
        )

        if not currencies:
            self.stdout.write(
                self.style.WARNING(
                    "El catálogo de monedas está vacío."
                )
            )
            return

        for currency in currencies:
            self.stdout.write("")
            self.stdout.write(
                f"CurrencyId={currency.currency_id}"
            )
            self.stdout.write(
                f"Nombre={currency.name}"
            )
            self.stdout.write(
                f"Descripción={currency.description}"
            )
