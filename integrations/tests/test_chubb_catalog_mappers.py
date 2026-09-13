from django.test import SimpleTestCase

from integrations.providers.chubb.catalog_mappers import (
    ChubbCatalogMapper,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
)


class ChubbCatalogSuburbsMapperTests(SimpleTestCase):

    def test_map_suburbs_mapea_respuesta_valida(self):
        payload = {
            "suburbs": [
                {
                    "suburbId": 12,
                    "suburbDescription": "CENTRO",
                    "countrySubdivisionId": 5,
                    "municipalityId": 369,
                    "populationId": 123,
                },
                {
                    "suburbId": 13,
                    "suburbDescription": "PARTIDO ROMERO",
                    "countrySubdivisionId": 5,
                    "municipalityId": 369,
                    "populationId": 124,
                },
            ]
        }

        result = ChubbCatalogMapper.map_suburbs(
            payload
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0].suburb_id,
            12,
        )

        self.assertEqual(
            result[0].name,
            "CENTRO",
        )

        self.assertEqual(
            result[0].description,
            "CENTRO",
        )

        self.assertEqual(
            result[0].country_subdivision_id,
            5,
        )

        self.assertEqual(
            result[0].municipality_id,
            369,
        )

        self.assertEqual(
            result[0].population_id,
            123,
        )

    def test_map_suburbs_rechaza_payload_sin_lista(
        self,
    ):
        with self.assertRaisesRegex(
            ProviderInvalidResponseError,
            "suburbs",
        ):
            ChubbCatalogMapper.map_suburbs(
                {
                    "suburbs": None,
                }
            )

    def test_map_suburbs_rechaza_suburb_id_invalido(
        self,
    ):
        payload = {
            "suburbs": [
                {
                    "suburbId": 0,
                    "suburbDescription": "CENTRO",
                }
            ]
        }

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            ChubbCatalogMapper.map_suburbs(
                payload
            )
