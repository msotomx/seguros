from __future__ import annotations

from integrations.persons.provider_resolver import (
    PersonProviderResolver,
)
from integrations.providers.chubb.person_provider_builder import (
    ChubbPersonProviderBuilder,
)


def build_person_provider_resolver() -> PersonProviderResolver:
    """
    Composition root de providers de personas.

    Registra las implementaciones disponibles en código.
    Toda configuración operativa continúa proviniendo de
    ProviderConfiguration.
    """

    builders = (
        ChubbPersonProviderBuilder(),
    )

    return PersonProviderResolver(
        builders={
            builder.provider_code: builder
            for builder in builders
        },
    )
