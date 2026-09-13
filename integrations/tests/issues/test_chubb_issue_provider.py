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


class ChubbIssueProviderTests(TestCase):

    def test_issue_coordinates_mapper_client_and_adapter(self):
        internal_request = InternalIssueRequest(
            provider_quote_id="144479063",
            provider_quote_version_id="1",
            payment_method_code="CONTADO",
            insured=IssuePartyReference(
                provider_tran_id="57482667",
                provider_person_id="18683522",
                provider_address_id="1410484013",
            ),
            risks=(),
            invoice=None,
        )

        chubb_request = Mock(
            spec=ChubbIssueRequest
        )

        chubb_result = ChubbIssueResult(
            quote_key="M6",
            quote_policy_id=99007664,
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

        request_mapper = Mock()
        request_mapper.issue.return_value = (
            chubb_request
        )

        client = Mock()
        client.issue.return_value = (
            chubb_result
        )

        provider = ChubbIssueProvider(
            client=client,
            request_mapper=request_mapper,
        )

        result = provider.issue(
            internal_request
        )

        request_mapper.issue.assert_called_once_with(
            internal_request
        )

        client.issue.assert_called_once_with(
            chubb_request
        )

        self.assertEqual(
            result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            result.provider_policy_id,
            "99007664",
        )
        self.assertEqual(
            result.provider_policy_key,
            "M6",
        )
        self.assertIsNone(
            result.policy_number
        )
