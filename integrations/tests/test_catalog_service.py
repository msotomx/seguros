from django.test import TestCase

from integrations.catalog.services import CatalogService
from integrations.catalog.exceptions import (
    CatalogItemNotFoundError,
    CatalogNotFoundError,
    ProviderCatalogMappingNotFoundError,
)
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)


class CatalogServiceTest(TestCase):
    def setUp(self):
        self.provider = AseguradoraConfiguracion.objects.create(
            # Ajusta estos campos a los obligatorios de tu modelo.
            nombre="Chubb Test",
        )

        self.catalog = Catalog.objects.create(
            code="VEHICLE_USE",
            name="Uso del vehículo",
            is_active=True,
        )

        self.particular = CatalogItem.objects.create(
            catalog=self.catalog,
            code="PARTICULAR",
            name="Particular",
            sort_order=1,
            is_active=True,
        )

        self.commercial = CatalogItem.objects.create(
            catalog=self.catalog,
            code="COMMERCIAL",
            name="Comercial",
            sort_order=2,
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.provider,
            catalog=self.catalog,
            catalog_item=self.particular,
            external_code="01",
            external_name="Particular",
            is_active=True,
        )

    def test_get_item(self):
        result = CatalogService.get_item(
            catalog_code="vehicle_use",
            internal_code="particular",
        )

        self.assertEqual(result.catalog_code, "VEHICLE_USE")
        self.assertEqual(result.internal_code, "PARTICULAR")
        self.assertEqual(result.name, "Particular")

    def test_list_items(self):
        results = CatalogService.list_items(
            catalog_code="vehicle_use",
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].internal_code, "PARTICULAR")
        self.assertEqual(results[1].internal_code, "COMMERCIAL")

    def test_to_provider(self):
        result = CatalogService.to_provider(
            provider_id=self.provider.id,
            catalog_code="vehicle_use",
            internal_code="particular",
        )

        self.assertEqual(result.internal_code, "PARTICULAR")
        self.assertEqual(result.external_code, "01")
        self.assertEqual(result.external_name, "Particular")

    def test_from_provider(self):
        result = CatalogService.from_provider(
            provider_id=self.provider.id,
            catalog_code="vehicle_use",
            external_code="01",
        )

        self.assertEqual(result.external_code, "01")
        self.assertEqual(result.internal_code, "PARTICULAR")

    def test_catalog_not_found(self):
        with self.assertRaises(CatalogNotFoundError):
            CatalogService.get_item(
                catalog_code="UNKNOWN_CATALOG",
                internal_code="VALUE",
            )

    def test_catalog_item_not_found(self):
        with self.assertRaises(CatalogItemNotFoundError):
            CatalogService.get_item(
                catalog_code="VEHICLE_USE",
                internal_code="UNKNOWN",
            )

    def test_provider_mapping_not_found(self):
        with self.assertRaises(
            ProviderCatalogMappingNotFoundError
        ):
            CatalogService.to_provider(
                provider_id=self.provider.id,
                catalog_code="VEHICLE_USE",
                internal_code="COMMERCIAL",
            )

    def test_inactive_mapping_is_not_resolved(self):
        mapping = ProviderCatalogMapping.objects.get(
            provider=self.provider,
            catalog_item=self.particular,
        )
        mapping.is_active = False
        mapping.save()

        with self.assertRaises(
            ProviderCatalogMappingNotFoundError
        ):
            CatalogService.to_provider(
                provider_id=self.provider.id,
                catalog_code="VEHICLE_USE",
                internal_code="PARTICULAR",
            )
            