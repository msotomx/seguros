from __future__ import annotations

from integrations.issues.adapters.issue_adapter import (
    ChubbIssueAdapter,
)
from integrations.issues.contracts import (
    InternalIssueRequest,
    IssueResult,
)
from integrations.providers.chubb.internal_issue_mapper import (
    ChubbInternalIssueRequestMapper,
)
from integrations.providers.chubb.issue_client import (
    ChubbIssueClient,
)


class ChubbIssueProvider:
    """
    Adaptador entre IssueService y la integración
    específica de Chubb.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        client: ChubbIssueClient,
        request_mapper: ChubbInternalIssueRequestMapper,
    ) -> None:
        self._client = client
        self._request_mapper = request_mapper

    def issue(
        self,
        request: InternalIssueRequest,
    ) -> IssueResult:
        chubb_request = self._request_mapper.issue(
            request
        )

        chubb_result = self._client.issue(
            chubb_request
        )

        return ChubbIssueAdapter.to_issue_result(
            chubb_result
        )
