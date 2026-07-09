from django.core.management.base import BaseCommand

from integrations.providers.insurance.chubb.services.catalog_service import ChubbCatalogService
from integrations.providers.insurance.chubb.exceptions import ChubbProviderError


class Command(BaseCommand):
    help = "Prueba conexión con Chubb API"

    def handle(self, *args, **options):
        service = ChubbCatalogService()

        self.stdout.write("Probando /health...")
        try:
            health = service.health()
            self.stdout.write(self.style.SUCCESS(f"Health OK: {health}"))
        except ChubbProviderError as exc:
            self.stdout.write(self.style.ERROR(f"Health error: {exc}"))

        self.stdout.write("Probando /catalogs/business-profiles...")
        try:
            profiles = service.business_profiles(system_name="SEMI")
            self.stdout.write(self.style.SUCCESS(f"Business profiles OK: {profiles}"))
        except ChubbProviderError as exc:
            self.stdout.write(self.style.ERROR(f"Business profiles error: {exc}"))
