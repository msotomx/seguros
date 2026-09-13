from datetime import date

from django.test import SimpleTestCase

from integrations.persons.contracts import (
    PersonAddress,
    PersonRequest,
)
from integrations.providers.chubb.internal_person_mapper import (
    ChubbInternalPersonRequestMapper,
)


class ChubbInternalPersonRequestMapperTests(SimpleTestCase):

    def setUp(self):
        self.mapper = ChubbInternalPersonRequestMapper(
            person_type_id=None,
            legal_personality_id=0,
            marital_status_id=1,
            address_type_id=1,
            gender_ids={
                "MASCULINO": 1,
                "FEMENINO": 2,
            },
        )

        self.request = PersonRequest(
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
                city="Ciudad Juarez",
                state="Chihuahua",
                postal_code="32500",
            ),
        )

    def test_create_person_mapea_contrato_interno_a_chubb(self):
        result = self.mapper.create_person(
            request=self.request,
            neighborhood_id=13083,
        )

        self.assertIsNone(
            result.person_type_id,
        )

        self.assertEqual(
            result.legal_personality_id,
            0,
        )

        self.assertEqual(
            result.rfc,
            "SOLM800101",
        )

        self.assertEqual(
            result.homo_clave,
            "ABC",
        )

        self.assertEqual(
            result.first_name,
            "Miguel",
        )

        self.assertEqual(
            result.second_name,
            "",
        )

        self.assertEqual(
            result.paternal_surname,
            "Soto",
        )

        self.assertEqual(
            result.maternal_surname,
            "Lopez",
        )

        self.assertEqual(
            result.birth_or_constitution_date,
            date(1980, 1, 1),
        )

        self.assertEqual(
            result.gender_id,
            1,
        )

        self.assertEqual(
            result.curp,
            "SOLM800101HCHXXX00",
        )

        self.assertEqual(
            result.marital_status_id,
            1,
        )

        self.assertEqual(
            result.address.address_type_id,
            1,
        )

        self.assertEqual(
            result.address.street,
            "Av. Tecnologico",
        )

        self.assertEqual(
            result.address.exterior_number,
            "1234",
        )

        self.assertIsNone(
            result.address.interior_number,
        )

        self.assertEqual(
            result.address.neighborhood_id,
            13083,
        )

        self.assertEqual(
            result.email,
            "miguel@example.com",
        )

        self.assertEqual(
            result.personal_phone.area_code,
            "656",
        )

        self.assertEqual(
            result.personal_phone.number,
            "1234567",
        )

        self.assertEqual(
            result.cell_phone.area_code,
            "656",
        )

        self.assertEqual(
            result.cell_phone.number,
            "1234567",
        )

    def test_create_person_rechaza_genero_no_configurado(self):
        request = PersonRequest(
            first_name=self.request.first_name,
            paternal_surname=self.request.paternal_surname,
            maternal_surname=self.request.maternal_surname,
            rfc=self.request.rfc,
            birth_date=self.request.birth_date,
            gender="NO_CONFIGURADO",
            email=self.request.email,
            phone=self.request.phone,
            curp=self.request.curp,
            address=self.request.address,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Género no configurado",
        ):
            self.mapper.create_person(
                request=request,
                neighborhood_id=13083,
            )

    def test_create_person_rechaza_rfc_invalido(self):
        request = PersonRequest(
            first_name=self.request.first_name,
            paternal_surname=self.request.paternal_surname,
            maternal_surname=self.request.maternal_surname,
            rfc="RFCINVALIDO",
            birth_date=self.request.birth_date,
            gender=self.request.gender,
            email=self.request.email,
            phone=self.request.phone,
            curp=self.request.curp,
            address=self.request.address,
        )

        with self.assertRaisesRegex(
            ValueError,
            "13 caracteres",
        ):
            self.mapper.create_person(
                request=request,
                neighborhood_id=13083,
            )

    def test_create_person_rechaza_telefono_invalido(self):
        request = PersonRequest(
            first_name=self.request.first_name,
            paternal_surname=self.request.paternal_surname,
            maternal_surname=self.request.maternal_surname,
            rfc=self.request.rfc,
            birth_date=self.request.birth_date,
            gender=self.request.gender,
            email=self.request.email,
            phone="65612345",
            curp=self.request.curp,
            address=self.request.address,
        )

        with self.assertRaisesRegex(
            ValueError,
            "10 dígitos",
        ):
            self.mapper.create_person(
                request=request,
                neighborhood_id=13083,
            )

    def test_create_person_rechaza_neighborhood_id_invalido(self):
        with self.assertRaisesRegex(
            ValueError,
            "mayor que cero",
        ):
            self.mapper.create_person(
                request=self.request,
                neighborhood_id=0,
            )
