from unittest.mock import Mock

from django.test import TestCase

from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)
from integrations.providers.chubb.contracts import ChubbSuburb
from integrations.providers.chubb.suburb_sync_service import (
    ChubbSuburbSyncService,
)


class ChubbSuburbSyncServiceTests(TestCase):
    def setUp(self):
        self.provider = AseguradoraConfiguracion.objects.create(
            nombre="Chubb Test",
        )

        self.catalog = Catalog.objects.create(
            code="SUBURB",
            name="Colonias",
            is_active=True,
        )

        self.catalog_client = Mock()

    def test_sync_crea_items_y_mappings(self):
        self.catalog_client.suburbs.return_value = (
            ChubbSuburb(
                suburb_id=12,
                name="CENTRO",
                description="CENTRO",
                country_subdivision_id=5,
                municipality_id=369,
                population_id=100,
            ),
            ChubbSuburb(
                suburb_id=13,
                name="PARTIDO ROMERO",
                description="PARTIDO ROMERO",
                country_subdivision_id=5,
                municipality_id=369,
                population_id=100,
            ),
        )

        result = ChubbSuburbSyncService.sync(
            provider_id=self.provider.id,
            zip_code="32500",
            catalog_client=self.catalog_client,
        )

        self.catalog_client.suburbs.assert_called_once_with(
            zip_code="32500",
        )

        self.assertEqual(len(result), 2)

        centro = CatalogItem.objects.get(
            catalog=self.catalog,
            code="32500_CENTRO",
        )

        self.assertEqual(centro.name, "CENTRO")
        self.assertEqual(
            centro.metadata["zip_code"],
            "32500",
        )
        self.assertEqual(
            centro.metadata["municipality_id"],
            369,
        )

        mapping = ProviderCatalogMapping.objects.get(
            provider=self.provider,
            catalog_item=centro,
        )

        self.assertEqual(mapping.external_code, "12")
        self.assertEqual(mapping.external_name, "CENTRO")

    def test_sync_normaliza_nombre_para_codigo_interno(self):
        self.catalog_client.suburbs.return_value = (
            ChubbSuburb(
                suburb_id=25,
                name="JARDINES DE SAN JOSÉ",
                description="JARDINES DE SAN JOSÉ",
                municipality_id=369,
            ),
        )

        ChubbSuburbSyncService.sync(
            provider_id=self.provider.id,
            zip_code="32500",
            catalog_client=self.catalog_client,
        )

        self.assertTrue(
            CatalogItem.objects.filter(
                catalog=self.catalog,
                code="32500_JARDINES_DE_SAN_JOSE",
            ).exists()
        )

    def test_sync_es_idempotente(self):
        suburb = ChubbSuburb(
            suburb_id=12,
            name="CENTRO",
            description="CENTRO",
            municipality_id=369,
        )

        self.catalog_client.suburbs.return_value = (
            suburb,
        )

        first = ChubbSuburbSyncService.sync(
            provider_id=self.provider.id,
            zip_code="32500",
            catalog_client=self.catalog_client,
        )

        second = ChubbSuburbSyncService.sync(
            provider_id=self.provider.id,
            zip_code="32500",
            catalog_client=self.catalog_client,
        )

        self.assertEqual(
            CatalogItem.objects.filter(
                catalog=self.catalog,
            ).count(),
            1,
        )

        self.assertEqual(
            ProviderCatalogMapping.objects.filter(
                provider=self.provider,
                catalog=self.catalog,
            ).count(),
            1,
        )

        self.assertEqual(
            first[0].id,
            second[0].id,
        )

    def test_sync_rechaza_codigo_postal_vacio(self):
        with self.assertRaises(ValueError):
            ChubbSuburbSyncService.sync(
                provider_id=self.provider.id,
                zip_code="",
                catalog_client=self.catalog_client,
            )

        self.catalog_client.suburbs.assert_not_called()
