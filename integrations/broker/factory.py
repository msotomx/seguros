from integrations.providers.insurance.chubb.provider import ChubbProvider

"""
Factory del Switchh Insurance Engine.

Responsable de crear e inicializar la instancia del Insurance Provider
correspondiente a una aseguradora.

Recibe el código del Provider y su configuración, devolviendo una
implementación lista para ser utilizada por el Insurance Broker.

No contiene lógica de negocio.
No realiza llamadas HTTP.
No conoce modelos Django.
"""

def get_provider(code, provider_config=None):
    providers = {
        "CHUBB": ChubbProvider,
    }

    provider_class = providers.get(code)

    if not provider_class:
        raise ValueError(f"Proveedor no soportado: {code}")

    return provider_class(provider_config=provider_config)
