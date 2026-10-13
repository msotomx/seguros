from datetime import date
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)
from integrations.providers.chubb.contracts import (
    ChubbAccessToken,
    ChubbHttpResponse,
)
from integrations.providers.chubb.person_client import (
    ChubbPersonClient,
)
from integrations.providers.chubb.person_contracts import (
    ChubbCreatePersonRequest,
    ChubbCreatePersonResult,
    ChubbPersonAddressRequest,
    ChubbPersonPhoneRequest,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


def _create_person_request():
    phone = ChubbPersonPhoneRequest(
        area_code="656",
        number="1234567",
    )

    return ChubbCreatePersonRequest(
        person_type_id=None,
        legal_personality_id=0,
        rfc="SOLM800101",
        homo_clave="ABC",
        first_name="Miguel",
        second_name="",
        paternal_surname="Soto",
        maternal_surname="Lopez",
        birth_or_constitution_date=date(1980, 1, 1),
        gender_id=1,
        curp="SOLM800101HCHXXX00",
        marital_status_id=1,
        address=ChubbPersonAddressRequest(
            address_type_id=1,
            street="Av. Tecnologico",
            exterior_number="1234",
            interior_number=None,
            neighborhood_id=13083,
        ),
        email="miguel@example.com",
        personal_phone=phone,
        cell_phone=phone,
    )


class ChubbPersonClientTests(SimpleTestCase):

    def setUp(self):
        self.configuration = ProviderConfiguration(
            id=1,
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            nombre="Chubb SIT Autos",
            base_url="https://quote.example.test",
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
        self.auth_client.get_token.return_value = (
            self.token
        )

        self.http_client = Mock()

        self.client = ChubbPersonClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        self.request = _create_person_request()

        self.request_payload = {
            "rfc": "SOLM800101",
            "homoClave": "ABC",
        }

        self.response_payload = {
            "tranId": 60486498,
            "personId": 18683522,
            "addressId": 1410484013,
        }

        self.http_response = ChubbHttpResponse(
            status_code=200,
            data=self.response_payload,
            headers={},
        )

        self.result = Mock(
            spec=ChubbCreatePersonResult,
        )

    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonResponseMapper.create_person"
    )
    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonRequestMapper.create_person"
    )
    def test_create_person_posts_payload_with_source_application_header(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = (
            self.request_payload
        )
        self.http_client.post.return_value = (
            self.http_response
        )
        response_mapper_mock.return_value = self.result

        self.client.create_person(self.request)

        self.http_client.post.assert_called_once_with(
            "/person",
            token=self.token,
            payload=self.request_payload,
            headers={
                "CB-SourceApplication": "23",
            },
        )

    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonResponseMapper.create_person"
    )
    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonRequestMapper.create_person"
    )
    def test_create_person_calls_request_mapper(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = (
            self.request_payload
        )
        self.http_client.post.return_value = (
            self.http_response
        )
        response_mapper_mock.return_value = self.result

        self.client.create_person(self.request)

        request_mapper_mock.assert_called_once_with(
            self.request
        )

    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonResponseMapper.create_person"
    )
    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonRequestMapper.create_person"
    )
    def test_create_person_maps_http_response(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = (
            self.request_payload
        )
        self.http_client.post.return_value = (
            self.http_response
        )
        response_mapper_mock.return_value = self.result

        result = self.client.create_person(
            self.request
        )

        response_mapper_mock.assert_called_once_with(
            self.response_payload
        )

        self.assertIs(result, self.result)

    def test_create_person_rejects_invalid_request_type(
        self,
    ):
        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "request debe ser ChubbCreatePersonRequest",
        ):
            self.client.create_person({})

        self.http_client.post.assert_not_called()

    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonRequestMapper.create_person"
    )
    def test_create_person_preserves_request_mapper_error_as_cause(
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
            self.client.create_person(
                self.request
            )

        self.assertIs(
            context.exception.__cause__,
            mapper_error,
        )

        self.http_client.post.assert_not_called()

    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonResponseMapper.create_person"
    )
    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbPersonRequestMapper.create_person"
    )
    def test_create_person_preserves_response_mapper_error_as_cause(
        self,
        request_mapper_mock,
        response_mapper_mock,
    ):
        request_mapper_mock.return_value = (
            self.request_payload
        )
        self.http_client.post.return_value = (
            self.http_response
        )

        mapper_error = ValueError(
            "Respuesta inválida."
        )
        response_mapper_mock.side_effect = mapper_error

        with self.assertRaises(
            ProviderInvalidResponseError
        ) as context:
            self.client.create_person(
                self.request
            )

        self.assertIs(
            context.exception.__cause__,
            mapper_error,
        )

    def test_uses_explicit_configuration_without_get_active(
        self,
    ):
        self.configuration_service.reset_mock()

        client = ChubbPersonClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=(
                self.configuration_service
            ),
            configuration=self.configuration,
            auth_client=self.auth_client,
            http_client=self.http_client,
        )

        self.assertIs(
            client.configuration,
            self.configuration,
        )

        self.configuration_service.get_active.assert_not_called()

    @patch(
        "integrations.providers.chubb.person_client."
        "ChubbAuthClient"
    )
    def test_passes_explicit_configuration_to_auth_client(
        self,
        auth_client_class,
    ):
        self.configuration_service.reset_mock()

        ChubbPersonClient(
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            configuration=self.configuration,
            http_client=self.http_client,
        )

        self.configuration_service.get_active.assert_not_called()

        auth_client_class.assert_called_once_with(
            provider="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            configuration_service=self.configuration_service,
            configuration=self.configuration,
        )
