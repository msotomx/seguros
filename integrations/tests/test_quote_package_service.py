from django.test import TestCase

from integrations.catalog.quote_package_service import (
    QuotePackageService,
)
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)


class QuotePackageServiceTests(TestCase):

    def setUp(self):
        self.configuration = (
            AseguradoraConfiguracion.objects.create(
                provider="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
                nombre="Chubb SIT Test",
                base_url="https://chubb.test",
                activo=True,
                supports_quote=True,
            )
        )

        self.catalog = Catalog.objects.create(
            code="COVERAGE_PACKAGE",
            name="Paquetes de cobertura",
            is_active=True,
        )

        self.amplia = CatalogItem.objects.create(
            catalog=self.catalog,
            code="AMPLIA",
            name="Amplia",
            sort_order=10,
            is_active=True,
        )

        self.limitada = CatalogItem.objects.create(
            catalog=self.catalog,
            code="LIMITADA",
            name="Limitada",
            sort_order=20,
            is_active=True,
        )

        self.rc = CatalogItem.objects.create(
            catalog=self.catalog,
            code="RC",
            name="Responsabilidad Civil",
            sort_order=30,
            is_active=True,
        )

    def test_list_internal_codes_for_provider_regresa_mapeos_activos(
        self,
    ):
        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.amplia,
            external_code="1",
            external_name="Amplia",
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.limitada,
            external_code="2",
            external_name="Limitada",
            is_active=True,
        )

        result = (
            QuotePackageService
            .list_internal_codes_for_provider(
                provider_id=self.configuration.id,
            )
        )

        self.assertEqual(
            result,
            (
                "AMPLIA",
                "LIMITADA",
            ),
        )

    def test_list_internal_codes_for_provider_respeta_orden_catalogo(
        self,
    ):
        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.rc,
            external_code="3",
            external_name="RC",
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.amplia,
            external_code="1",
            external_name="Amplia",
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.limitada,
            external_code="2",
            external_name="Limitada",
            is_active=True,
        )

        result = (
            QuotePackageService
            .list_internal_codes_for_provider(
                provider_id=self.configuration.id,
            )
        )

        self.assertEqual(
            result,
            (
                "AMPLIA",
                "LIMITADA",
                "RC",
            ),
        )

    def test_list_internal_codes_for_provider_excluye_mapeos_inactivos(
        self,
    ):
        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.amplia,
            external_code="1",
            external_name="Amplia",
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.limitada,
            external_code="2",
            external_name="Limitada",
            is_active=False,
        )

        result = (
            QuotePackageService
            .list_internal_codes_for_provider(
                provider_id=self.configuration.id,
            )
        )

        self.assertEqual(
            result,
            (
                "AMPLIA",
            ),
        )

    def test_list_internal_codes_for_provider_rechaza_provider_id_invalido(
        self,
    ):
        for value in (
            0,
            -1,
            None,
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    (
                        QuotePackageService
                        .list_internal_codes_for_provider(
                            provider_id=value,
                        )
                    )
