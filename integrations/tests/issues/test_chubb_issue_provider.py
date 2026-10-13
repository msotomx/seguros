from unittest import TestCase
from unittest.mock import Mock

from integrations.issues.contracts import (
    InternalIssueRequest,
    IssuePartyReference,
)
from integrations.providers.chubb.issue_contracts import (
    ChubbIssueRequest,
    ChubbIssueResult,
)
from integrations.providers.chubb.issue_provider import (
    ChubbIssueProvider,
)
from integrations.catalog.contracts import (
    ProviderCatalogValue,
)

class ChubbIssueProviderTests(TestCase):

    def test_issue_coordinates_mapper_client_and_adapter(self):
        client = Mock()
        request_mapper = Mock()
        catalog_service = Mock()

        catalog_service.to_provider.return_value = (
            ProviderCatalogValue(
                provider_id=1,
                catalog_code="PAYMENT_TYPE",
                internal_code="CONTADO",
                internal_name="Contado",
                external_code="12",
                external_name="Contado",
                metadata={},
            )
        )

        chubb_request = Mock()
        request_mapper.issue.return_value = chubb_request

        chubb_result = ChubbIssueResult(
            quote_key="M6",
            quote_policy_id=99007670,
            net_premium_amount=35247.21,
            bonification_amount=0.0,
            surcharge_amount=0.0,
            discount_amount=0.0,
            total_premium_amount=41582.77,
            insured_id=18683522,
            insured_address_id=1410484013,
            items=(),
            raw_response={
                "success": True,
            },
        )

        client.issue.return_value = chubb_result
        request = InternalIssueRequest(
            provider_quote_id="2061261215",
            provider_quote_version_id="2061499999",
            payment_method_code="CONTADO",
            insured=IssuePartyReference(
                provider_tran_id="57482667",
                provider_person_id="18683522",
                provider_address_id="1410484013",
            ),
            risks=(),
            invoice=None,
        )

        provider = ChubbIssueProvider(
            provider_id=1,
            client=client,
            request_mapper=request_mapper,
            catalog_service=catalog_service,
        )

        result = provider.issue(
            request,
        )

        catalog_service.to_provider.assert_called_once_with(
            provider_id=1,
            catalog_code="PAYMENT_TYPE",
            internal_code="CONTADO",
        )

        request_mapper.issue.assert_called_once_with(
            request,
            payment_type_id=12,
        )

        client.issue.assert_called_once_with(
            chubb_request,
        )

        self.assertEqual(
            result.provider_code,
            "CHUBB",
        )

        self.assertEqual(
            result.provider_policy_id,
            "99007670",
        )
