from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.providers.chubb.quote_adapter import ChubbQuoteAdapter
from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
    ChubbQuoteContext,
)
from integrations.providers.contracts import (
    QuoteAmount,
    QuoteInsured,
    QuoteRequest,
    QuoteResponse,
    QuoteVehicle,
)
from integrations.providers.exceptions import (
    ProviderQuoteError,
    ProviderUnsupportedOperationError,
)


class ChubbAdapterTest(SimpleTestCase):
    def setUp(self):
        self.auth_client = Mock()
        self.context_resolver = Mock()

        self.http_client = Mock()
        self.payload_builder = Mock()
        self.response_mapper = Mock()

        self.token = ChubbAccessToken(
            access_token="test-token",
            token_type="Bearer",
            expires_in=3599,
            resource="test-resource",
        )

        self.context = ChubbQuoteContext(
            product_id=1,
            business_profile_id=7190,
            agent_id=93300,
            conduit_id=0,
            grouping_id=353796,
            rate_id=453,
            calculation_type_id=2,
            currency_id=1,
            payment_type_id=12,
            vehicle_key="01140300301",
            vehicle_id=1146,
            insured_amount_type_id=1,
            deductible_type_id=1,
            country_subdivision_id=1,
            municipality_id=42,
            vehicle_use_id=1,
            package_id=1,
        )

        self.request = QuoteRequest(
            provider_id=1,
            vehicle=QuoteVehicle(
                year=2024,
                brand_code="NISSAN",
                model_code="VERSA",
                version_code="ADVANCE",
                use_code="PARTICULAR",
                postal_code="31000",
            ),
            insured=QuoteInsured(
                person_type="INDIVIDUAL",
                first_name="Miguel",
                last_name="Soto",
            ),
            start_date=date(2026, 7, 11),
            end_date=date(2027, 7, 11),
            payment_frequency_code="ANNUAL",
            coverage_code="COMPREHENSIVE",
            metadata={
                "state_code": "CHH",
                "municipality_code": "CHIHUAHUA",
            },
        )

        self.quote_payload = {
            "productId": 1,
            "items": [],
        }

        self.quote_headers = {
            "CB-SourceApplication": "23",
        }

        self.chubb_payload = {
            "success": True,
            "messages": [],
            "responseData": {
                "quoteId": 124469636,
                "quoteVersionId": 126717156,
                "baseNetPremium": 1000,
                "feeAmount": 100,
                "taxAmount": 176,
                "totalPremiumAmount": 1276,
            },
        }

        self.expected_response = QuoteResponse(
            provider_id=1,
            provider_quote_id="124469636",
            status="QUOTED",
            amount=QuoteAmount(
                net_premium=Decimal("1000"),
                fees=Decimal("100"),
                taxes=Decimal("176"),
                total=Decimal("1276"),
                currency="MXN",
            ),
            metadata={
                "quote_version_id": "126717156",
            },
        )

        self.auth_client.get_token.return_value = (
            self.token
        )

        self.context_resolver.resolve.return_value = (
            self.context
        )

        self.payload_builder.build.return_value = (
            self.quote_payload
        )

        self.payload_builder.build_headers.return_value = (
            self.quote_headers
        )

        self.http_client.post.return_value = (
            SimpleNamespace(
                status_code=200,
                data=self.chubb_payload,
                headers={},
            )
        )

        self.response_mapper.map.return_value = (
            self.expected_response
        )

        self.adapter = ChubbQuoteAdapter(
            provider_id=1,
            ambiente="SIT",
            ramo="AUTOS",
            auth_client=self.auth_client,
            context_resolver=self.context_resolver,
            http_client=self.http_client,
            payload_builder=self.payload_builder,
            response_mapper=self.response_mapper,
        )

    def test_provider_identity(self):
        self.assertEqual(
            self.adapter.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            self.adapter.provider_id,
            1,
        )

    def test_supports_quote(self):
        self.assertTrue(
            self.adapter.supports("quote")
        )

    def test_rejects_unsupported_operation(self):
        with self.assertRaises(
            ProviderUnsupportedOperationError
        ):
            self.adapter.ensure_supported(
                "issue_policy"
            )

    def test_quote_executes_complete_pipeline(self):
        response = self.adapter.quote(
            request=self.request,
        )

        self.assertEqual(
            response,
            self.expected_response,
        )

        self.auth_client.get_token.assert_called_once_with()

        self.context_resolver.resolve.assert_called_once_with(
            request=self.request,
        )

        self.payload_builder.build.assert_called_once_with(
            request=self.request,
            context=self.context,
        )

        (
            self.payload_builder
            .build_headers
            .assert_called_once_with(
                context=self.context,
            )
        )

        self.http_client.post.assert_called_once_with(
            "/quote",
            token=self.token,
            payload=self.quote_payload,
            headers=self.quote_headers,
        )

        self.response_mapper.map.assert_called_once_with(
            provider_id=1,
            payload=self.chubb_payload,
        )

    def test_authenticate_delegates_to_auth_client(self):
        token = self.adapter.authenticate()

        self.assertEqual(token, self.token)

        self.auth_client.get_token.assert_called_once_with()

    def test_rejects_request_for_another_provider(self):
        invalid_request = QuoteRequest(
            provider_id=2,
            vehicle=self.request.vehicle,
            insured=self.request.insured,
            start_date=self.request.start_date,
            end_date=self.request.end_date,
            payment_frequency_code=(
                self.request.payment_frequency_code
            ),
            coverage_code=self.request.coverage_code,
            metadata=self.request.metadata,
        )

        with self.assertRaises(ProviderQuoteError):
            self.adapter.quote(
                request=invalid_request,
            )

        self.auth_client.get_token.assert_not_called()
        self.http_client.post.assert_not_called()

    def test_propagates_normalized_provider_error(self):
        self.auth_client.get_token.side_effect = (
            ProviderQuoteError(
                "Error controlado de Chubb."
            )
        )

        with self.assertRaises(
            ProviderQuoteError
        ) as context:
            self.adapter.quote(
                request=self.request,
            )

        self.assertEqual(
            str(context.exception),
            "Error controlado de Chubb.",
        )

    def test_wraps_unexpected_error(self):
        self.context_resolver.resolve.side_effect = (
            RuntimeError("unexpected")
        )

        with self.assertRaises(
            ProviderQuoteError
        ) as context:
            self.adapter.quote(
                request=self.request,
            )

        self.assertIn(
            "error inesperado",
            str(context.exception).lower(),
        )
        