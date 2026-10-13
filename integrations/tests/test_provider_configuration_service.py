from django.test import TestCase

from catalogos.models import (
    Aseguradora,
    ProductoSeguro,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.models import (
    AseguradoraConfiguracion,
)
from integrations.configuration.exceptions import (
    ProviderConfigurationNotFound,
)


class ProviderConfigurationServiceTests(TestCase):

    def setUp(self):
        self.chubb = Aseguradora.objects.create(
            nombre="CHUBB TEST",
        )

        self.axa = Aseguradora.objects.create(
            nombre="AXA TEST",
        )

        self.qualitas = Aseguradora.objects.create(
            nombre="QUALITAS TEST",
        )

        self.chubb_producto = ProductoSeguro.objects.create(
            aseguradora=self.chubb,
            nombre_producto="Chubb Auto Test",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.axa_producto = ProductoSeguro.objects.create(
            aseguradora=self.axa,
            nombre_producto="AXA Auto Test",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.qualitas_producto = ProductoSeguro.objects.create(
            aseguradora=self.qualitas,
            nombre_producto="Qualitas Auto Test",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.chubb_config = (
            AseguradoraConfiguracion.objects.create(
                aseguradora=self.chubb,
                producto_seguro=self.chubb_producto,
                provider="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
                nombre="Chubb SIT",
                base_url="https://chubb.test",
                activo=True,
                prioridad=20,
                supports_quote=True,
            )
        )

        self.axa_config = (
            AseguradoraConfiguracion.objects.create(
                aseguradora=self.axa,
                producto_seguro=self.axa_producto,
                provider="AXA",
                ambiente="SIT",
                ramo="AUTOS",
                nombre="AXA SIT",
                base_url="https://axa.test",
                activo=True,
                prioridad=10,
                supports_quote=True,
            )
        )

        self.qualitas_config = (
            AseguradoraConfiguracion.objects.create(
                aseguradora=self.qualitas,
                producto_seguro=self.qualitas_producto,
                provider="QUALITAS",
                ambiente="SIT",
                ramo="AUTOS",
                nombre="Qualitas SIT",
                base_url="https://qualitas.test",
                activo=True,
                prioridad=5,
                supports_quote=False,
            )
        )

    def test_list_active_for_quote_filtra_y_ordena(
        self,
    ):
        configurations = (
            ProviderConfigurationService
            .list_active_for_quote(
                ambiente="SIT",
                ramo="AUTOS",
            )
        )

        self.assertEqual(
            len(configurations),
            2,
        )

        self.assertEqual(
            [
                configuration.provider
                for configuration in configurations
            ],
            [
                "AXA",
                "CHUBB",
            ],
        )

    def test_list_active_for_quote_expone_relaciones_comerciales(
        self,
    ):
        configurations = (
            ProviderConfigurationService
            .list_active_for_quote(
                ambiente="SIT",
                ramo="AUTOS",
            )
        )

        chubb = next(
            configuration
            for configuration in configurations
            if configuration.provider == "CHUBB"
        )

        self.assertEqual(
            chubb.aseguradora_id,
            self.chubb.id,
        )

        self.assertEqual(
            chubb.producto_seguro_id,
            self.chubb_producto.id,
        )

    def test_get_active_usa_misma_conversion(
        self,
    ):
        configuration = (
            ProviderConfigurationService.get_active(
                provider="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
            )
        )

        self.assertEqual(
            configuration.id,
            self.chubb_config.id,
        )

        self.assertEqual(
            configuration.aseguradora_id,
            self.chubb.id,
        )

        self.assertEqual(
            configuration.producto_seguro_id,
            self.chubb_producto.id,
        )

        self.assertTrue(
            configuration.supports_quote,
        )

    def test_get_by_id_devuelve_configuracion_activa(self):
        configuration = (
            ProviderConfigurationService.get_by_id(
                self.chubb_config.id,
            )
        )

        self.assertEqual(
            configuration.id,
            self.chubb_config.id,
        )

        self.assertEqual(
            configuration.provider,
            "CHUBB",
        )

        self.assertEqual(
            configuration.aseguradora_id,
            self.chubb.id,
        )

        self.assertEqual(
            configuration.producto_seguro_id,
            self.chubb_producto.id,
        )

    def test_get_by_id_rechaza_id_invalido(self):
        with self.assertRaisesRegex(
            ValueError,
            "configuration_id debe ser un entero positivo",
        ):
            ProviderConfigurationService.get_by_id(0)

    def test_get_by_id_no_devuelve_configuracion_inactiva(self):
        self.chubb_config.activo = False
        self.chubb_config.save(
            update_fields=["activo"],
        )

        with self.assertRaises(Exception):
            ProviderConfigurationService.get_by_id(
                self.chubb_config.id,
            )

    def test_get_by_id_no_devuelve_configuracion_inactiva(self):
        self.chubb_config.activo = False
        self.chubb_config.save(
            update_fields=["activo"],
        )

        with self.assertRaises(
            ProviderConfigurationNotFound,
        ):
            ProviderConfigurationService.get_by_id(
                self.chubb_config.id,
            )

