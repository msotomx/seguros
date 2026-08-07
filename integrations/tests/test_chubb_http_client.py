from unittest.mock import Mock

import requests
from django.test import SimpleTestCase

from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
)
from integrations.providers.chubb.http_client import (
    ChubbHttpClient,
)
from integrations.providers.exceptions import (
    ProviderHttpConnectionError,
    ProviderHttpResponseError,
    ProviderHttpTimeoutError,
    ProviderInvalidResponseError,
)


class ChubbHttpClientTest(SimpleTestCase):
    def setUp(self):
        self.session = Mock()

        self.client = ChubbHttpClient(
            base_url="https://sit.example.com/digital.quote.partners/",
            api_version="1",
            timeout=20,
            session=self.session,
        )

        self.token = ChubbAccessToken(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=3599,
            resource="test-resource",
        )

    def test_get_sends_expected_headers_and_params(self):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"makes": []}'
        response.headers = {
            "Content-Type": "application/json",
        }
        response.json.return_value = {
            "makes": [],
        }

        self.session.request.return_value = response

        result = self.client.get(
            "/catalogs/vehicles/makes",
            token=self.token,
            params={
                "BusinessProfileName": "TEST",
                "GroupingId": 1,
            },
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, {"makes": []})

        self.session.request.assert_called_once_with(
            method="GET",
            url=(
                "https://sit.example.com/"
                "digital.quote.partners/"
                "catalogs/vehicles/makes"
            ),
            headers={
                "Accept": "application/json",
                "Authorization": (
                    "Bearer test-access-token"
                ),
                "apiVersion": "1",
            },
            params={
                "BusinessProfileName": "TEST",
                "GroupingId": 1,
            },
            timeout=20,
            allow_redirects=False,
        )

    def test_post_sends_json_payload(self):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"quotedId": 123}'
        response.headers = {}
        response.json.return_value = {
            "quotedId": 123,
        }

        self.session.request.return_value = response

        payload = {
            "vehicle": {
                "year": 2024,
            },
        }

        result = self.client.post(
            "/quotes",
            token=self.token,
            payload=payload,
        )

        self.assertEqual(
            result.data["quotedId"],
            123,
        )

        self.session.request.assert_called_once_with(
            method="POST",
            url=(
                "https://sit.example.com/"
                "digital.quote.partners/quotes"
            ),
            headers={
                "Accept": "application/json",
                "Authorization": (
                    "Bearer test-access-token"
                ),
                "apiVersion": "1",
            },
            params={},
            timeout=20,
            allow_redirects=False,
            json=payload,
        )

    def test_custom_headers_are_added(self):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"ok": true}'
        response.headers = {}
        response.json.return_value = {
            "ok": True,
        }

        self.session.request.return_value = response

        self.client.get(
            "/catalogs/test",
            token=self.token,
            headers={
                "SystemName": "SWITCHH",
            },
        )

        called_headers = (
            self.session.request
            .call_args
            .kwargs["headers"]
        )

        self.assertEqual(
            called_headers["SystemName"],
            "SWITCHH",
        )

    def test_timeout_is_normalized(self):
        self.session.request.side_effect = (
            requests.Timeout()
        )

        with self.assertRaises(
            ProviderHttpTimeoutError
        ):
            self.client.get(
                "/catalogs/test",
                token=self.token,
            )

    def test_connection_error_is_normalized(self):
        self.session.request.side_effect = (
            requests.ConnectionError()
        )

        with self.assertRaises(
            ProviderHttpConnectionError
        ):
            self.client.get(
                "/catalogs/test",
                token=self.token,
            )

    def test_http_error_is_normalized(self):
        response = Mock()
        response.ok = False
        response.status_code = 400
        response.json.return_value = {
            "message": "Solicitud inválida",
        }

        self.session.request.return_value = response

        with self.assertRaises(
            ProviderHttpResponseError
        ) as context:
            self.client.post(
                "/quotes",
                token=self.token,
                payload={},
            )

        self.assertIn(
            "Solicitud inválida",
            str(context.exception),
        )

    def test_invalid_json_is_rejected(self):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.content = b"not-json"
        response.headers = {}
        response.json.side_effect = ValueError()

        self.session.request.return_value = response

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            self.client.get(
                "/catalogs/test",
                token=self.token,
            )

    def test_empty_response_returns_none(self):
        response = Mock()
        response.ok = True
        response.status_code = 204
        response.content = b""
        response.headers = {}

        self.session.request.return_value = response

        result = self.client.post(
            "/quotes/test",
            token=self.token,
            payload={},
        )

        self.assertIsNone(result.data)
