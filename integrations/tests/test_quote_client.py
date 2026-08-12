from __future__ import annotations
from datetime import date
from unittest.mock import Mock, patch
from django.test import SimpleTestCase

from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)
from integrations.providers.chubb.quote_client import (
    ChubbQuoteClient,
)
from integrations.providers.chubb.quote_contracts import (
    ChubbCreateQuoteRequest,
    ChubbCreateQuoteResult,
    ChubbQuoteItemRequest,
    ChubbQuotePaymentTypeRequest,
)
from integrations.broker.provider_configuration import ProviderConfiguration
from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
    ChubbHttpResponse,
)


def _create_quote_request() -> ChubbCreateQuoteRequest:
    """
    Request mínimo válido para probar ChubbQuoteClient.

    Las pruebas del mapper ya verifican el contenido completo de items,
    vehículos, paquetes y coberturas. Aquí sólo necesitamos un contrato
    reconocible, porque el RequestMapper será simulado.
    """

    return ChubbCreateQuoteRequest(
        product_id=1,
        business_profile_id=7195,
        agent_id="AGENTE-01",
        conduit_id=0,
        grouping_id=353991,
        rate_id=308,
        effective_date=date(2026, 7, 29),
        expiration_date=date(2027, 7, 29),
        calculation_type_id=1,
        currency_id=1,
        reference="COT-0001",
        prospect_name="Miguel Soto",
        payment_types=(
            ChubbQuotePaymentTypeRequest(
                payment_type_id=1,
            ),
        ),
        items=(
            ChubbQuoteItemRequest(
                risk_id=0,
                risk_number=1,
                discounts=(),
                vehicle=None,
                packages=(),
            ),
        ),
    )


class ChubbQuoteClientTests(SimpleTestCase):
    def setUp(self) -> None:
        self.configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT Autos",
            base_url="https://chubb.example.test",
            api_version="1",
            timeout=30,
            source_application_id=23,
        )

        self.configuration_service = Mock()
        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.token = ChubbAccessToken(
            access_token="test-token",
            token_type="Bearer",
            expires_in=3600,
        )

        self.auth_client = Mock()
        self.auth_client.get_token.return_value = self.token

        self.http_client = Mock()

        self.client = ChubbQuoteClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        self.request = _create_quote_request()

        self.request_payload = {
            "productId": 1,
            "reference": "COT-0001",
        }

        self.response_payload = {
            "success": True,
            "responseData": {
                "quoteId": 12345,
            },
        }

        self.http_response = ChubbHttpResponse(
            status_code=200,
            data=self.response_payload,
            headers={},
        )

        self.result = Mock(
            spec=ChubbCreateQuoteResult,
        )

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_posts_payload_with_source_application_header(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload
        self.http_client.post.return_value = self.http_response
        response_mapper_mock.return_value = self.result

        self.client.create_quote(self.request)

        self.http_client.post.assert_called_once_with(
            "/quote",
            token=self.token,
            payload=self.request_payload,
            headers={
                "CB-SourceApplication": str(
                    self.configuration.source_application_id
                ),
            },
        )

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_calls_request_mapper_with_request(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload
        self.http_client.post.return_value = self.http_response
        response_mapper_mock.return_value = self.result

        self.client.create_quote(self.request)

        request_mapper_mock.assert_called_once_with(
            self.request,
        )

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_maps_http_response(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload
        self.http_client.post.return_value = self.http_response        
        response_mapper_mock.return_value = self.result

        self.client.create_quote(self.request)

        response_mapper_mock.assert_called_once_with(
            self.response_payload,
        )

    def test_create_quote_rejects_invalid_request_type(self):
        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "request debe ser ChubbCreateQuoteRequest",
        ):
            self.client.create_quote({})

        self.http_client.post.assert_not_called()

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_does_not_call_http_when_request_mapper_fails(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.side_effect = ValueError(
            "agent_id no puede estar vacío."
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "agent_id no puede estar vacío",
        ):
            self.client.create_quote(self.request)

        self.http_client.post.assert_not_called()
        response_mapper_mock.assert_not_called()

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_preserves_request_mapper_error_as_cause(
        self,
        request_mapper_mock,
    ):
        mapper_error = ValueError(
            "Solicitud inválida."
        )
        request_mapper_mock.side_effect = mapper_error

        with self.assertRaises(
            ProviderInvalidResponseError
        ) as context:
            self.client.create_quote(self.request)

        self.assertIs(
            context.exception.__cause__,
            mapper_error,
        )

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_converts_response_mapper_value_error(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload
        self.http_client.post.return_value = self.http_response
        response_mapper_mock.side_effect = ValueError(
            "responseData es requerido."
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "responseData es requerido",
        ):
            self.client.create_quote(self.request)

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_preserves_response_mapper_error_as_cause(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload
        self.http_client.post.return_value = self.http_response

        mapper_error = ValueError(
            "Respuesta inválida."
        )
        response_mapper_mock.side_effect = mapper_error

        with self.assertRaises(
            ProviderInvalidResponseError
        ) as context:
            self.client.create_quote(self.request)

        self.assertIs(
            context.exception.__cause__,
            mapper_error,
        )

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_does_not_call_response_mapper_when_http_fails(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload

        http_error = RuntimeError(
            "No fue posible conectar con Chubb."
        )
        self.http_client.post.side_effect = http_error

        with self.assertRaises(RuntimeError) as context:
            self.client.create_quote(self.request)

        self.assertIs(
            context.exception,
            http_error,
        )
        response_mapper_mock.assert_not_called()

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_propagates_http_client_provider_error(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = self.request_payload

        provider_error = ProviderInvalidResponseError(
            "Chubb devolvió una respuesta inválida."
        )
        self.http_client.post.side_effect = provider_error

        with self.assertRaises(
            ProviderInvalidResponseError
        ) as context:
            self.client.create_quote(self.request)

        self.assertIs(
            context.exception,
            provider_error,
        )
        response_mapper_mock.assert_not_called()

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteResponseMapper.create_quote"
    )
    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote"
    )
    def test_create_quote_executes_operations_in_expected_order(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        calls = []

        def map_request(request):
            calls.append("request_mapper")
            return self.request_payload

        def post(
            path,
            *,
            token,
            payload,
            headers,
        ):
            self.assertEqual(path, "/quote")
            self.assertIs(token, self.token)
            self.assertEqual(payload, self.request_payload)
            self.assertEqual(
                headers,
                {
                    "CB-SourceApplication": "23",
                },
            )

            calls.append("http_post")
            return self.http_response

        def map_response(response):
            calls.append("response_mapper")
            return self.result

        request_mapper_mock.side_effect = map_request
        self.http_client.post.side_effect = post
        response_mapper_mock.side_effect = map_response

        result = self.client.create_quote(self.request)

        self.assertIs(result, self.result)
        self.assertEqual(
            calls,
            [
                "request_mapper",
                "http_post",
                "response_mapper",
            ],
        )

    @patch(
        "integrations.providers.chubb.quote_client."
        "ChubbQuoteRequestMapper.create_quote",
        return_value={
            "productId": 1,
            "reference": "COT-0001",
        },
    )
    def test_create_quote_fails_when_source_application_id_is_missing(
        self,
        request_mapper_mock,
    ):
        configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT Autos",
            base_url="https://chubb.example.test",
            api_version="1",
            timeout=30,
            source_application_id=None,
        )

        self.configuration_service.get_active.return_value = (
            configuration
        )

        client = ChubbQuoteClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "source_application_id",
        ):
            client.create_quote(self.request)

        self.auth_client.get_token.assert_not_called()
        self.http_client.post.assert_not_called()

    def test_constructor_loads_active_configuration(self):
        self.configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

    def test_get_quote_executes_get_and_maps_response(self):
        response_payload = {
            "messages": [],
            "responseData": {
                "quoteId": 2061090336,
                "quoteVersionId": 2061333219,
                "baseNetPremium": 16984.7275,
                "baseNetPremiumWithoutDiscount": 16984.7275,
                "surchargePercentage": 0.0,
                "surchargeAmount": 0.0,
                "feeAmount": 600.0,
                "taxPercentage": 0.16,
                "taxAmount": 2813.5564,
                "totalPremiumAmount": 20398.2839,
                "commissionPorcentage": 0.0,
                "commissionAmount": 0.0,
                "surchargeCommissionAmount": 0.0,
                "items": [
                    {
                        "riskNumber": 1,
                        "packages": [
                            {
                                "packageId": 1,
                                "riskId": 2061468037,
                                "selected": True,
                                "totalPremiumAmount": 20398.2839,
                                "vehicle": {
                                    "vehicleKey": "010101001001",
                                },
                                "coverages": [],
                            },
                        ],
                    },
                ],
            },
        }

        self.http_client.get.return_value = ChubbHttpResponse(
            status_code=200,
            data=response_payload,
            headers={},
        )

        expected_result = Mock(
            spec=ChubbCreateQuoteResult,
        )

        with patch(
            "integrations.providers.chubb.quote_client."
            "ChubbQuoteResponseMapper.get_quote"
        ) as mapper_mock:
            mapper_mock.return_value = expected_result

            result = self.client.get_quote(
                2061090336
            )

        self.auth_client.get_token.assert_called_once_with()

        self.http_client.get.assert_called_once_with(
            "/quote",
            token=self.token,
            params={
                "quoteId": 2061090336,
            },
        )

        mapper_mock.assert_called_once_with(
            response_payload
        )

        self.assertIs(
            result,
            expected_result,
        )

    def test_get_quote_rejects_invalid_quote_id(self):
        invalid_values = (
            0,
            -1,
            True,
            None,
            "2061090336",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.client.get_quote(
                        value
                    )
