from __future__ import annotations

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.documents.provider_resolver import (
    DocumentProviderResolver,
)
from integrations.providers.chubb.document_provider_builder import (
    ChubbDocumentProviderBuilder,
)


def build_document_provider_resolver(
    *,
    configuration_service=ProviderConfigurationService,
) -> DocumentProviderResolver:
    return DocumentProviderResolver(
        builders={
            ChubbDocumentProviderBuilder.provider_code: (
                ChubbDocumentProviderBuilder(
                    configuration_service=(
                        configuration_service
                    ),
                )
            ),
        },
    )
