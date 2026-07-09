from django.core.management.base import BaseCommand

from integrations.broker.factory import get_provider


class Command(BaseCommand):
    help = "Prueba motor broker de aseguradoras"

    def add_arguments(self, parser):
        parser.add_argument("--provider", default="CHUBB")

    def handle(self, *args, **options):
        provider = get_provider(options["provider"])

        self.stdout.write(f"Probando proveedor: {provider.name}")

        result = provider.health()

        self.stdout.write(self.style.SUCCESS(f"Health OK: {result}"))
