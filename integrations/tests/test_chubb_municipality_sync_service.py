from unittest.mock import Mock

from django.test import TestCase

from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)
from integrations.providers.chubb.contracts import (
    ChubbMunicipality,
)
from integrations.providers.chubb.municipality_sync_service import (
    ChubbMunicipalitySyncService,
)


class ChubbMunicipalitySyncServiceTests(TestCase):
    def setUp(self):
        self.provider = (
            AseguradoraConfiguracion.objects.create(
                nombre="Chubb Test",
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=308,
            )
        )

        self.state_catalog = Catalog.objects.create(
            code="STATE",
            name="Estados",
            is_active=True,
        )

        self.municipality_catalog = (
            Catalog.objects.create(
                code="MUNICIPALITY",
                name="Municipios",
                is_active=True,
            )
        )

        self.state_item = CatalogItem.objects.create(
            catalog=self.state_catalog,
            code="CHIHUAHUA",
            name="Chihuahua",
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.provider,
            catalog=self.state_catalog,
            catalog_item=self.state_item,
            external_code="5",
            external_name="CHIHUAHUA",
            metadata={},
            is_active=True,
        )

        self.catalog_client = Mock()

    def test_sync_crea_items_y_mappings(self):
        self.catalog_client.municipalities.return_value = (
            ChubbMunicipality(
                municipality_id=369,
                name="CHIHUAHUA",
                description="CHIHUAHUA",
            ),
            ChubbMunicipality(
                municipality_id=370,
                name="JUAREZ",
                description="JUAREZ",
            ),
        )

        result = ChubbMunicipalitySyncService.sync(
            provider_id=self.provider.id,
            state_internal_code="CHIHUAHUA",
            catalog_client=self.catalog_client,
        )

        self.catalog_client.municipalities.assert_called_once_with(
            country_subdivision_id=5,
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=308,
        )

        self.assertEqual(len(result), 2)

        juarez = CatalogItem.objects.get(
            catalog=self.municipality_catalog,
            code="JUAREZ",
        )

        self.assertEqual(
            juarez.name,
            "JUAREZ",
        )

        mapping = ProviderCatalogMapping.objects.get(
            provider=self.provider,
            catalog_item=juarez,
        )

        self.assertEqual(
            mapping.external_code,
            "370",
        )

        self.assertEqual(
            mapping.external_name,
            "JUAREZ",
        )

        self.assertEqual(
            mapping.metadata[
                "country_subdivision_id"
            ],
            5,
        )

    def test_sync_normaliza_acentos_del_codigo(self):
        self.catalog_client.municipalities.return_value = (
            ChubbMunicipality(
                municipality_id=370,
                name="JUÁREZ",
                description="JUÁREZ",
            ),
        )

        ChubbMunicipalitySyncService.sync(
            provider_id=self.provider.id,
            state_internal_code="chihuahua",
            catalog_client=self.catalog_client,
        )

        self.assertTrue(
            CatalogItem.objects.filter(
                catalog=self.municipality_catalog,
                code="JUAREZ",
            ).exists()
        )

    def test_sync_es_idempotente(self):
        municipality = ChubbMunicipality(
            municipality_id=369,
            name="CHIHUAHUA",
            description="CHIHUAHUA",
        )

        self.catalog_client.municipalities.return_value = (
            municipality,
        )

        first = ChubbMunicipalitySyncService.sync(
            provider_id=self.provider.id,
            state_internal_code="CHIHUAHUA",
            catalog_client=self.catalog_client,
        )

        second = ChubbMunicipalitySyncService.sync(
            provider_id=self.provider.id,
            state_internal_code="CHIHUAHUA",
            catalog_client=self.catalog_client,
        )

        self.assertEqual(
            CatalogItem.objects.filter(
                catalog=self.municipality_catalog,
            ).count(),
            1,
        )

        self.assertEqual(
            ProviderCatalogMapping.objects.filter(
                provider=self.provider,
                catalog=self.municipality_catalog,
            ).count(),
            1,
        )

        self.assertEqual(
            first[0].id,
            second[0].id,
        )

    def test_sync_falla_si_no_existe_mapping_del_estado(
        self,
    ):
        ProviderCatalogMapping.objects.filter(
            provider=self.provider,
            catalog=self.state_catalog,
        ).delete()

        with self.assertRaisesRegex(
            ValueError,
            "No existe un mapping activo de STATE",
        ):
            ChubbMunicipalitySyncService.sync(
                provider_id=self.provider.id,
                state_internal_code="CHIHUAHUA",
                catalog_client=self.catalog_client,
            )

        self.catalog_client.municipalities.assert_not_called()

    def test_sync_rechaza_codigo_de_estado_vacio(self):
        with self.assertRaises(ValueError):
            ChubbMunicipalitySyncService.sync(
                provider_id=self.provider.id,
                state_internal_code="",
                catalog_client=self.catalog_client,
            )

        self.catalog_client.municipalities.assert_not_called()
