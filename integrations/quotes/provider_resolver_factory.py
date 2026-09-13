from __future__ import annotations

from integrations.providers.chubb.quote_provider_builder import (
    ChubbQuoteProviderBuilder,
)
from integrations.quotes.provider_resolver import (
    QuoteProviderResolver,
)


def build_quote_provider_resolver() -> QuoteProviderResolver:
    """
    Composition root de providers de cotización.

    Registra las implementaciones disponibles en código.
    Toda configuración operativa continúa proviniendo de
    ProviderConfiguration.
    """

    builders = (
        ChubbQuoteProviderBuilder(),
    )

    return QuoteProviderResolver(
        builders={
            builder.provider_code: builder
            for builder in builders
        },
    )
