from django.test import TestCase

from integrations.catalog.mapping_write_service import (
    CatalogMappingWriteService,
)
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)


class CatalogMappingWriteServiceTests(TestCase):
    def setUp(self):
        self.provider = AseguradoraConfiguracion.objects.create(
            nombre="Chubb Test",
        )

        self.catalog = Catalog.objects.create(
            code="SUBURB",
            name="Colonias",
            is_active=True,
        )

    def test_upsert_crea_item_y_mapping(self):
        result = CatalogMappingWriteService.upsert(
            provider_id=self.provider.id,
            catalog_code="SUBURB",
            internal_code="32500_CENTRO",
            internal_name="Centro",
            external_code="12",
            external_name="CENTRO",
            metadata={
                "zip_code": "32500",
            },
        )

        item = CatalogItem.objects.get(
            catalog=self.catalog,
            code="32500_CENTRO",
        )

        mapping = ProviderCatalogMapping.objects.get(
            provider=self.provider,
            catalog_item=item,
        )

        self.assertEqual(result.id, mapping.id)

        self.assertEqual(item.name, "Centro")
        self.assertEqual(
            item.metadata,
            {
                "zip_code": "32500",
            },
        )

        self.assertEqual(mapping.catalog, self.catalog)
        self.assertEqual(mapping.external_code, "12")
        self.assertEqual(mapping.external_name, "CENTRO")
        self.assertTrue(mapping.is_active)

    def test_upsert_es_idempotente(self):
        first = CatalogMappingWriteService.upsert(
            provider_id=self.provider.id,
            catalog_code="SUBURB",
            internal_code="32500_CENTRO",
            internal_name="Centro",
            external_code="12",
            external_name="CENTRO",
        )

        second = CatalogMappingWriteService.upsert(
            provider_id=self.provider.id,
            catalog_code="SUBURB",
            internal_code="32500_CENTRO",
            internal_name="Centro",
            external_code="12",
            external_name="CENTRO",
        )

        self.assertEqual(first.id, second.id)

        self.assertEqual(
            CatalogItem.objects.filter(
                catalog=self.catalog,
                code="32500_CENTRO",
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

    def test_upsert_actualiza_mapping_existente(self):
        first = CatalogMappingWriteService.upsert(
            provider_id=self.provider.id,
            catalog_code="SUBURB",
            internal_code="32500_CENTRO",
            internal_name="Centro",
            external_code="12",
            external_name="CENTRO",
        )

        second = CatalogMappingWriteService.upsert(
            provider_id=self.provider.id,
            catalog_code="SUBURB",
            internal_code="32500_CENTRO",
            internal_name="Centro actualizado",
            external_code="15",
            external_name="CENTRO ACTUALIZADO",
            metadata={
                "zip_code": "32500",
                "municipality_id": 369,
            },
        )

        self.assertEqual(first.id, second.id)

        item = CatalogItem.objects.get(
            catalog=self.catalog,
            code="32500_CENTRO",
        )

        mapping = ProviderCatalogMapping.objects.get(
            pk=first.pk,
        )

        self.assertEqual(
            item.name,
            "Centro actualizado",
        )
        self.assertEqual(
            item.metadata["municipality_id"],
            369,
        )

        self.assertEqual(
            mapping.external_code,
            "15",
        )
        self.assertEqual(
            mapping.external_name,
            "CENTRO ACTUALIZADO",
        )

    def test_upsert_reactiva_item_y_mapping(self):
        item = CatalogItem.objects.create(
            catalog=self.catalog,
            code="32500_CENTRO",
            name="Centro",
            is_active=False,
        )

        mapping = ProviderCatalogMapping.objects.create(
            provider=self.provider,
            catalog=self.catalog,
            catalog_item=item,
            external_code="12",
            external_name="CENTRO",
            is_active=False,
        )

        result = CatalogMappingWriteService.upsert(
            provider_id=self.provider.id,
            catalog_code="SUBURB",
            internal_code="32500_CENTRO",
            internal_name="Centro",
            external_code="12",
            external_name="CENTRO",
        )

        item.refresh_from_db()
        mapping.refresh_from_db()

        self.assertEqual(result.id, mapping.id)
        self.assertTrue(item.is_active)
        self.assertTrue(mapping.is_active)
