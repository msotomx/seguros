from django.core.management.base import BaseCommand

from integrations.broker.registry import ProviderRegistry


class Command(BaseCommand):
    help = "Prueba Provider Registry del Motor Broker"

    def handle(self, *args, **options):
        self.stdout.write("Providers registrados:")

        for provider in ProviderRegistry.all():
            self.stdout.write(
                f"- {provider.code} | {provider.name} | "
                f"ramo={provider.ramo} | active={provider.active} | "
                f"priority={provider.priority} | quote={provider.supports_quote}"
            )

        self.stdout.write("")
        self.stdout.write("Providers activos para AUTOS:")

        for code in ProviderRegistry.quote_provider_codes(ramo="AUTOS"):
            self.stdout.write(self.style.SUCCESS(f"- {code}"))
