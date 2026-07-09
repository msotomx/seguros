"""
Ese registro respondería preguntas como:

¿Qué aseguradoras están activas?
¿Qué ramo manejan? (Autos, Gastos Médicos, Vida...)
¿En qué ambiente están? (SIT, UAT, Producción)
¿Cuál soporta emisión inmediata?
¿Cuál permite pago en línea?
¿Cuál tiene mejor prioridad?

"""
from dataclasses import dataclass

from integrations.broker.factory import get_provider


@dataclass(frozen=True)
class ProviderRegistration:
    code: str
    name: str
    ramo: str = "AUTOS"
    active: bool = True
    priority: int = 100
    supports_quote: bool = True
    supports_issue: bool = False
    supports_documents: bool = False


class ProviderRegistry:
    """
    Registro central de proveedores disponibles para el Motor Broker.

    Por ahora vive en código.
    Después leerá de AseguradoraConfiguracion.
    """

    _providers = [
        ProviderRegistration(
            code="CHUBB",
            name="Chubb",
            ramo="AUTOS",
            active=True,
            priority=1,
            supports_quote=True,
            supports_issue=False,
            supports_documents=False,
        ),
    ]

    @classmethod
    def all(cls):
        return sorted(cls._providers, key=lambda p: p.priority)

    @classmethod
    def active(cls, ramo: str | None = None):
        providers = [p for p in cls._providers if p.active]

        if ramo:
            providers = [p for p in providers if p.ramo == ramo]

        return sorted(providers, key=lambda p: p.priority)

    @classmethod
    def active_codes(cls, ramo: str | None = None):
        return [p.code for p in cls.active(ramo=ramo)]

    @classmethod
    def quote_providers(cls, ramo: str = "AUTOS"):
        providers = [
            p for p in cls.active(ramo=ramo)
            if p.supports_quote
        ]

        return sorted(providers, key=lambda p: p.priority)

    @classmethod
    def quote_provider_codes(cls, ramo: str = "AUTOS"):
        return [p.code for p in cls.quote_providers(ramo=ramo)]

    @classmethod
    def get_provider_instances(cls, ramo: str = "AUTOS"):
        return [
            get_provider(p.code)
            for p in cls.quote_providers(ramo=ramo)
        ]
