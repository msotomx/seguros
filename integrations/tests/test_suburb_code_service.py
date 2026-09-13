from django.test import SimpleTestCase

from integrations.catalog.suburb_code_service import (
    SuburbCodeService,
)


class SuburbCodeServiceTests(SimpleTestCase):

    def test_construye_codigo_con_cp_y_colonia(self):
        result = SuburbCodeService.build(
            zip_code="32500",
            name="Tecnologico",
        )

        self.assertEqual(
            result,
            "32500_TECNOLOGICO",
        )

    def test_normaliza_acentos_espacios_y_caracteres(self):
        result = SuburbCodeService.build(
            zip_code=" 32500 ",
            name="  Jardínes de San José  ",
        )

        self.assertEqual(
            result,
            "32500_JARDINES_DE_SAN_JOSE",
        )

    def test_rechaza_codigo_postal_vacio(self):
        with self.assertRaisesRegex(
            ValueError,
            "zip_code no puede estar vacío",
        ):
            SuburbCodeService.build(
                zip_code="",
                name="Tecnologico",
            )

    def test_rechaza_nombre_colonia_vacio(self):
        with self.assertRaisesRegex(
            ValueError,
            "nombre de la colonia no puede estar vacío",
        ):
            SuburbCodeService.build(
                zip_code="32500",
                name="",
            )
