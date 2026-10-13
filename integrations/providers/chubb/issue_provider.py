from integrations.catalog import CatalogService
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
    provider_code = "CHUBB"

    PAYMENT_TYPE_CATALOG_CODE = "PAYMENT_TYPE"

    def __init__(
        self,
        *,
        provider_id: int,
        client: ChubbIssueClient,
        request_mapper: ChubbInternalIssueRequestMapper,
        catalog_service=CatalogService,
    ):
        if (
            isinstance(provider_id, bool)
            or not isinstance(provider_id, int)
            or provider_id <= 0
        ):
            raise ValueError(
                "provider_id debe ser un entero positivo."
            )

        self._provider_id = provider_id
        self._client = client
        self._request_mapper = request_mapper
        self._catalog_service = catalog_service

    def issue(
        self,
        request: InternalIssueRequest,
    ) -> IssueResult:
        payment_type = self._catalog_service.to_provider(
            provider_id=self._provider_id,
            catalog_code=self.PAYMENT_TYPE_CATALOG_CODE,
            internal_code=request.payment_method_code,
        )

        payment_type_id = self._positive_int(
            payment_type.external_code,
            "PAYMENT_TYPE.external_code",
        )

        chubb_request = self._request_mapper.issue(
            request,
            payment_type_id=payment_type_id,
        )

        chubb_result = self._client.issue(
            chubb_request,
        )

        return ChubbIssueAdapter.to_issue_result(
            chubb_result,
        )

    @staticmethod
    def _positive_int(
        value,
        field_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} debe ser un entero positivo."
            )

        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field_name} debe ser un entero positivo."
            ) from exc

        if parsed <= 0:
            raise ValueError(
                f"{field_name} debe ser un entero positivo."
            )

        return parsed
