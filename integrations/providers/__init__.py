from __future__ import annotations

from typing import Optional

from integrations.providers.mock import MockProvider
from integrations.providers.mercadopago import MercadoPagoProvider

# Registra aquí providers reales cuando existan:
# from integrations.providers.stripe import StripeProvider

_PROVIDERS = {
    "mock": MockProvider(),
    "mercadopago": MercadoPagoProvider(),
    # "stripe": StripeProvider(),
    # "mercadopago": MercadoPagoProvider(),
}


def get_provider(slug: str) -> Optional[object]:
    if not slug:
        return None
    return _PROVIDERS.get(slug.lower())
