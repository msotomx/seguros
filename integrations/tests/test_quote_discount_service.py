from django.test import TestCase

from integrations.catalog.quote_discount_service import (
    QuoteDiscountService,
)
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)


class QuoteDiscountServiceTests(TestCase):

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
            code="DISCOUNT",
            name="Descuentos de cotización",
            is_active=True,
        )

        self.discount = CatalogItem.objects.create(
            catalog=self.catalog,
            code="DESCUENTO",
            name="Descuento",
            sort_order=10,
            is_active=True,
        )

        self.bonus = CatalogItem.objects.create(
            catalog=self.catalog,
            code="BONIFICACION",
            name="Bonificación",
            sort_order=20,
            is_active=True,
        )

    def test_list_internal_codes_for_provider_regresa_mapeos_activos(
        self,
    ):
        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.discount,
            external_code="1",
            external_name="Descuento",
            is_active=True,
        )

        ProviderCatalogMapping.objects.create(
            provider=self.configuration,
            catalog=self.catalog,
            catalog_item=self.bonus,
            external_code="2",
            external_name="Bonificacion",
            is_active=True,
        )

        result = (
            QuoteDiscountService
            .list_internal_codes_for_provider(
                provider_id=self.configuration.id,
            )
        )

        self.assertEqual(
            result,
            (
                "DESCUENTO",
                "BONIFICACION",
            ),
        )
