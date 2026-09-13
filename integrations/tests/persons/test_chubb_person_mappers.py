from datetime import date

from django.test import SimpleTestCase

from integrations.providers.chubb.person_contracts import (
    ChubbCreatePersonRequest,
    ChubbPersonAddressRequest,
    ChubbPersonPhoneRequest,
)
from integrations.providers.chubb.person_mappers import (
    ChubbPersonRequestMapper,
    ChubbPersonResponseMapper,
)


class ChubbPersonMapperTests(SimpleTestCase):

    def test_create_person_serializa_payload_chubb(self):
        request = ChubbCreatePersonRequest(
            person_type_id=None,
            legal_personality_id=0,
            rfc="DKHA920722",
            homo_clave="DS9",
            first_name="Hguo",
            second_name="Ruiz",
            paternal_surname="QA",
            maternal_surname="TESTING",
            birth_or_constitution_date=date(
                1992,
                7,
                22,
            ),
            gender_id=1,
            curp="CURP12345RT5",
            marital_status_id=1,
            address=ChubbPersonAddressRequest(
                address_type_id=1,
                street="BENITO JUAREZ",
                exterior_number="110",
                interior_number="307",
                neighborhood_id=12,
            ),
            email="api_test@yopmail.com",
            personal_phone=ChubbPersonPhoneRequest(
                area_code="85",
                number="55858745",
            ),
            cell_phone=ChubbPersonPhoneRequest(
                area_code="493",
                number="5534567",
            ),
        )

        payload = (
            ChubbPersonRequestMapper
            .create_person(request)
        )

        self.assertEqual(
            payload["rfc"],
            "DKHA920722",
        )

        self.assertEqual(
            payload["homoClave"],
            "DS9",
        )

        self.assertEqual(
            payload["birthOrConstitutionDate"],
            "1992-07-22",
        )

        self.assertEqual(
            payload["address"]["neighborhoodId"],
            12,
        )

        self.assertEqual(
            payload["cellPhone"],
            {
                "areaCode": "493",
                "number": "5534567",
            },
        )

    def test_create_person_parsea_ids_respuesta(
        self,
    ):
        payload = {
            "tranId": 60486498,
            "personId": 18683522,
            "addressId": 1410484013,
        }

        result = (
            ChubbPersonResponseMapper
            .create_person(payload)
        )

        self.assertEqual(
            result.tran_id,
            60486498,
        )

        self.assertEqual(
            result.person_id,
            18683522,
        )

        self.assertEqual(
            result.address_id,
            1410484013,
        )

    def test_create_person_rechaza_ids_invalidos(
        self,
    ):
        with self.assertRaises(ValueError):
            (
                ChubbPersonResponseMapper
                .create_person(
                    {
                        "tranId": 0,
                        "personId": 10,
                        "addressId": 20,
                    }
                )
            )
