from datetime import date
from unittest.mock import Mock

from django.test import SimpleTestCase

from integrations.persons.contracts import (
    PersonAddress,
    PersonRequest,
    PersonResult,
)
from integrations.persons.service import (
    PersonService,
)


class PersonServiceTests(SimpleTestCase):

    def _request(self):
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
                neighborhood_code="32500_CENTRO",
                city="Ciudad Juarez",
                state="Chihuahua",
                postal_code="32500",
            ),
        )


    def test_create_one_delega_en_provider(self):
        provider = Mock()
        provider.provider_code = "CHUBB"

        expected = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="100",
            provider_person_id="200",
            provider_address_id="300",
            raw_response={},
        )

        provider.create_person.return_value = expected

        service = PersonService(
            providers=[provider],
        )

        result = service.create_one(
            provider_code="CHUBB",
            request=self._request(),
        )

        self.assertEqual(
            result,
            expected,
        )

        provider.create_person.assert_called_once()

    def test_create_one_rechaza_provider_no_registrado(self):
        service = PersonService(
            providers=[],
        )

        with self.assertRaisesRegex(
            ValueError,
            "No existe PersonProvider",
        ):
            service.create_one(
                provider_code="CHUBB",
                request=self._request(),
            )
