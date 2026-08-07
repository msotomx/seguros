from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.providers.chubb.auth import (
    ChubbAuthClient,
)
from integrations.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
)


class ChubbAuthClientTest(SimpleTestCase):
    def setUp(self):
        self.configuration = SimpleNamespace(
            token_url=(
                "https://sit.example.com/"
                "enterprise.operations.authorization"
            ),
            client_id="test-app-id",
            client_secret="test-app-key",
            resource_id="test-resource",
            api_version="1",
            timeout=20,
            settings={
                "IDENTITY": "AAD",
            },
        )

        self.configuration_service = Mock()
        self.configuration_service.get_active.return_value = (
            self.configuration
        )

        self.session = Mock()

        self.client = ChubbAuthClient(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            session=self.session,
        )

    def test_get_token(self):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "token_type": "Bearer",
            "expires_in": "3599",
            "ext_expires_in": "3599",
            "expires_on": "1744351984",
            "not_before": "1744348084",
            "resource": "test-resource",
            "access_token": "test-access-token",
        }

        self.session.post.return_value = response

        token = self.client.get_token()

        self.assertEqual(
            token.access_token,
            "test-access-token",
        )
        self.assertEqual(token.token_type, "Bearer")
        self.assertEqual(token.expires_in, 3599)
        self.assertEqual(
            token.authorization_header,
            "Bearer test-access-token",
        )

        self.configuration_service.get_active.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.session.post.assert_called_once_with(
            self.configuration.token_url,
            params={
                "Identity": "AAD",
            },
            headers={
                "Content-Type": "application/json",
                "App_ID": "test-app-id",
                "App_Key": "test-app-key",
                "Resource": "test-resource",
                "apiVersion": "1",
            },
            json={},
            timeout=20,
        )


    def test_rejects_http_error(self):
        response = Mock()
        response.ok = False
        response.status_code = 401

        self.session.post.return_value = response

        with self.assertRaises(
            ProviderAuthenticationError
        ):
            self.client.get_token()

    def test_rejects_missing_access_token(self):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "token_type": "Bearer",
            "expires_in": "3599",
        }

        self.session.post.return_value = response

        with self.assertRaises(
            ProviderAuthenticationError
        ):
            self.client.get_token()

    def test_rejects_incomplete_configuration(self):
        self.configuration.client_secret = ""

        with self.assertRaises(
            ProviderConfigurationError
        ):
            self.client.get_token()
