from datetime import date
from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.catalog.contracts import (
    ProviderCatalogValue,
)
from integrations.persons.contracts import (
    PersonAddress,
    PersonRequest,
)
from integrations.providers.chubb.person_contracts import (
    ChubbCreatePersonRequest,
    ChubbCreatePersonResult,
)
from integrations.providers.chubb.person_provider import (
    ChubbPersonProvider,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


def _person_request() -> PersonRequest:
    return PersonRequest(
        first_name="Miguel",
        paternal_surname="Soto",
        maternal_surname="Lopez",
        rfc="SOLM800101ABC",
        birth_date=date(1980, 1, 1),
        gender="MASCULINO",
        email="miguel@example.com",
        phone="6561234567",
        curp="SOLM800101HCHXXX00",
        address=PersonAddress(
            street="Av. Tecnologico",
            exterior_number="1234",
            interior_number=None,
            neighborhood_code="32500_TECNOLOGICO",
            city="Juarez",
            state="Chihuahua",
            postal_code="32500",
        ),
    )


class ChubbPersonProviderTests(SimpleTestCase):

    def setUp(self):
        self.provider_id = 1

        self.client = Mock()
        self.request_mapper = Mock()
        self.catalog_service = Mock()

        self.provider = ChubbPersonProvider(
            provider_id=self.provider_id,
            client=self.client,
            request_mapper=self.request_mapper,
            catalog_service=self.catalog_service,
        )

        self.request = _person_request()

        self.provider_suburb = ProviderCatalogValue(
            provider_id=1,
            catalog_code="SUBURB",
            internal_code="32500_TECNOLOGICO",
            internal_name="TECNOLOGICO",
            external_code="13083",
            external_name="TECNOLOGICO",
            metadata={},
        )

        self.chubb_request = Mock(
            spec=ChubbCreatePersonRequest,
        )

        self.chubb_result = ChubbCreatePersonResult(
            tran_id=60486498,
            person_id=18683522,
            address_id=1410484013,
            raw_response={
                "tranId": 60486498,
                "personId": 18683522,
                "addressId": 1410484013,
            },
        )

    def test_create_person_resolves_suburb_for_provider(
        self,
    ):
        self.catalog_service.to_provider.return_value = (
            self.provider_suburb
        )
        self.request_mapper.create_person.return_value = (
            self.chubb_request
        )
        self.client.create_person.return_value = (
            self.chubb_result
        )

        self.provider.create_person(
            self.request
        )

        self.catalog_service.to_provider.assert_called_once_with(
            provider_id=1,
            catalog_code="SUBURB",
            internal_code="32500_TECNOLOGICO",
        )

    def test_create_person_maps_request_with_neighborhood_id(
        self,
    ):
        self.catalog_service.to_provider.return_value = (
            self.provider_suburb
        )
        self.request_mapper.create_person.return_value = (
            self.chubb_request
        )
        self.client.create_person.return_value = (
            self.chubb_result
        )

        self.provider.create_person(
            self.request
        )

        self.request_mapper.create_person.assert_called_once_with(
            request=self.request,
            neighborhood_id=13083,
        )

    def test_create_person_calls_client_with_chubb_request(
        self,
    ):
        self.catalog_service.to_provider.return_value = (
            self.provider_suburb
        )
        self.request_mapper.create_person.return_value = (
            self.chubb_request
        )
        self.client.create_person.return_value = (
            self.chubb_result
        )

        self.provider.create_person(
            self.request
        )

        self.client.create_person.assert_called_once_with(
            self.chubb_request
        )

    def test_create_person_returns_internal_result(
        self,
    ):
        self.catalog_service.to_provider.return_value = (
            self.provider_suburb
        )
        self.request_mapper.create_person.return_value = (
            self.chubb_request
        )
        self.client.create_person.return_value = (
            self.chubb_result
        )

        result = self.provider.create_person(
            self.request
        )

        self.assertEqual(
            result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            result.provider_tran_id,
            "60486498",
        )
        self.assertEqual(
            result.provider_person_id,
            "18683522",
        )
        self.assertEqual(
            result.provider_address_id,
            "1410484013",
        )
        self.assertEqual(
            result.raw_response,
            {
                "tranId": 60486498,
                "personId": 18683522,
                "addressId": 1410484013,
            },
        )

    def test_create_person_rejects_non_integer_suburb_external_code(
        self,
    ):
        self.catalog_service.to_provider.return_value = (
            ProviderCatalogValue(
                provider_id=1,
                catalog_code="SUBURB",
                internal_code="32500_TECNOLOGICO",
                internal_name="TECNOLOGICO",
                external_code="ABC",
                external_name="TECNOLOGICO",
                metadata={},
            )
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "SUBURB debe ser un identificador entero",
        ):
            self.provider.create_person(
                self.request
            )

        self.request_mapper.create_person.assert_not_called()
        self.client.create_person.assert_not_called()

    def test_create_person_rejects_non_positive_suburb_external_code(
        self,
    ):
        self.catalog_service.to_provider.return_value = (
            ProviderCatalogValue(
                provider_id=1,
                catalog_code="SUBURB",
                internal_code="32500_TECNOLOGICO",
                internal_name="TECNOLOGICO",
                external_code="0",
                external_name="TECNOLOGICO",
                metadata={},
            )
        )

        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "SUBURB debe ser mayor que cero",
        ):
            self.provider.create_person(
                self.request
            )

        self.request_mapper.create_person.assert_not_called()
        self.client.create_person.assert_not_called()
