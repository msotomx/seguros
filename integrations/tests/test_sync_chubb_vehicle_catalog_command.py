from io import StringIO
from unittest.mock import (
    Mock,
    patch,
)

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class SyncChubbVehicleCatalogCommandTests(
    SimpleTestCase
):
    @patch(
        "integrations.management.commands."
        "sync_chubb_vehicle_catalog."
        "ChubbCatalogClient"
    )
    def test_sin_send_solo_valida_configuracion(
        self,
        catalog_client_class,
    ):
        configuration = Mock()
        configuration.id = 17

        catalog_client = Mock()
        catalog_client.configuration = configuration

        catalog_client_class.return_value = (
            catalog_client
        )

        stdout = StringIO()

        call_command(
            "sync_chubb_vehicle_catalog",
            ambiente="sit",
            ramo="autos",
            vehicle_year=2024,
            stdout=stdout,
        )

        catalog_client_class.assert_called_once_with(
            ambiente="sit",
            ramo="autos",
        )

        output = stdout.getvalue()

        self.assertIn(
            "Provider config : 17",
            output,
        )

        self.assertIn(
            "No se consultó el catálogo del provider.",
            output,
        )

    @patch(
        "integrations.management.commands."
        "sync_chubb_vehicle_catalog."
        "ChubbVehicleCatalogSyncService"
    )
    @patch(
        "integrations.management.commands."
        "sync_chubb_vehicle_catalog."
        "ChubbCatalogClient"
    )
    def test_send_ejecuta_sync(
        self,
        catalog_client_class,
        sync_service,
    ):
        configuration = Mock()
        configuration.id = 17

        catalog_client = Mock()
        catalog_client.configuration = configuration

        catalog_client_class.return_value = (
            catalog_client
        )

        mapping_1 = Mock()
        mapping_2 = Mock()

        sync_service.sync.return_value = (
            mapping_1,
            mapping_2,
        )

        stdout = StringIO()

        call_command(
            "sync_chubb_vehicle_catalog",
            ambiente="sit",
            ramo="autos",
            vehicle_year=2024,
            send=True,
            stdout=stdout,
        )

        sync_service.sync.assert_called_once_with(
            provider_id=17,
            vehicle_year=2024,
            catalog_client=catalog_client,
        )

        self.assertIn(
            "Mapeos activos procesados: 2",
            stdout.getvalue(),
        )

    @patch(
        "integrations.management.commands."
        "sync_chubb_vehicle_catalog."
        "ChubbCatalogClient"
    )
    def test_rechaza_anio_fuera_de_rango(
        self,
        catalog_client_class,
    ):
        with self.assertRaises(CommandError):
            call_command(
                "sync_chubb_vehicle_catalog",
                ambiente="sit",
                ramo="autos",
                vehicle_year=1900,
            )

        catalog_client_class.assert_not_called()

    @patch(
        "integrations.management.commands."
        "sync_chubb_vehicle_catalog."
        "ChubbCatalogClient"
    )
    def test_error_de_configuracion_se_convierte_en_command_error(
        self,
        catalog_client_class,
    ):
        catalog_client_class.side_effect = ValueError(
            "Configuración inexistente"
        )

        with self.assertRaisesRegex(
            CommandError,
            "No fue posible resolver la configuración",
        ):
            call_command(
                "sync_chubb_vehicle_catalog",
                ambiente="sit",
                ramo="autos",
                vehicle_year=2024,
            )
