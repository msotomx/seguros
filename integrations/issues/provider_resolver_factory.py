from __future__ import annotations

from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.issues.provider_resolver import (
    IssueProviderResolver,
)
from integrations.providers.chubb.issue_provider_builder import (
    ChubbIssueProviderBuilder,
)


def build_issue_provider_resolver(
    *,
    configuration_service=ProviderConfigurationService,
) -> IssueProviderResolver:
    return IssueProviderResolver(
        builders={
            ChubbIssueProviderBuilder.provider_code: (
                ChubbIssueProviderBuilder(
                    configuration_service=(
                        configuration_service
                    ),
                )
            ),
        },
    )
