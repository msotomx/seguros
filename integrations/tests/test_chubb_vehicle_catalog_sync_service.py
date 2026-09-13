from unittest.mock import Mock

from django.test import TestCase

from autos.models import Marca, SubMarca, VehiculoCatalogo
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)
from integrations.providers.chubb.contracts import (
    ChubbVehicleData,
)
from integrations.providers.chubb.vehicle_catalog_sync_service import (
    ChubbVehicleCatalogSyncService,
)


class ChubbVehicleCatalogSyncServiceTests(TestCase):
    def setUp(self):
        self.provider = (
            AseguradoraConfiguracion.objects.create(
                nombre="Chubb Test",
                business_profile_name="BASE_TOM",
                grouping_id=353991,
                rate_id=308,
            )
        )

        self.catalog = Catalog.objects.create(
            code="VEHICLE",
            name="Vehículos",
            is_active=True,
        )

        self.catalog_client = Mock()

    def _vehicle(
        self,
        **overrides,
    ):
        data = {
            "vehicle_id": 64,
            "description": (
                "VAG 1.8L TIPTR L4 IMP/TUR AUT 4 "
                "D/ABS CA CE PIEL"
            ),
            "vehicle_type_id": 16,
            "trailer_id": 1,
            "tonnage_id": 7,
            "short_description": "A4 S LINE AUT",
            "long_description": (
                "VAG 1.8L TIPTR L4 IMP/TUR AUT 4 "
                "D/ABS CA CE PIEL"
            ),
            "tonnage": 0.0,
            "passengers": 5,
            "cmst": "010301002",
            "cmst_consecutive": 16,
            "active": True,
            "status": 1,
            "make_id": 3,
            "submake_id": 3,
            "vehicle_type_description": "A4",
            "trailer_type_description": "SIN REMOLQUE",
            "submake_description": "AUDI",
            "make_description": "AUDI",
            "tonnage_description": "Autos",
            "class_id": 1,
            "vehicle_group_id": 1,
            "vehicle_group_description": "300 M",
            "status_description": "Activo",
            "mtc": "030901",
            "vehicle_key": "01030100216",
            "vehicle_condition_id": 0,
        }

        data.update(overrides)

        return ChubbVehicleData(**data)

    def test_sync_crea_catalogo_interno_y_mapping(self):
        self.catalog_client.vehicle_data.return_value = (
            self._vehicle(),
        )

        result = ChubbVehicleCatalogSyncService.sync(
            provider_id=self.provider.id,
            vehicle_year=2024,
            catalog_client=self.catalog_client,
        )

        self.catalog_client.vehicle_data.assert_called_once_with(
            business_profile_name="BASE_TOM",
            grouping_id=353991,
            rate_id=308,
            vehicle_year=2024,
        )

        self.assertEqual(len(result), 1)

        marca = Marca.objects.get(
            nombre="AUDI",
        )

        submarca = SubMarca.objects.get(
            marca=marca,
            nombre="AUDI",
        )

        vehiculo = VehiculoCatalogo.objects.get(
            marca=marca,
            submarca=submarca,
            anio=2024,
        )

        self.assertEqual(
            vehiculo.version,
            "A4 S LINE AUT",
        )

        self.assertEqual(
            vehiculo.tipo_vehiculo,
            "A4",
        )

        self.assertEqual(
            vehiculo.clave_amis,
            "",
        )

        item = CatalogItem.objects.get(
            catalog=self.catalog,
            code=f"VEHICULO_CATALOGO_{vehiculo.pk}",
        )

        mapping = ProviderCatalogMapping.objects.get(
            provider=self.provider,
            catalog_item=item,
        )

        self.assertEqual(
            mapping.external_code,
            "01030100216",
        )

        self.assertEqual(
            mapping.metadata["vehicle_id"],
            64,
        )

        self.assertEqual(
            mapping.metadata["make_id"],
            3,
        )

        self.assertEqual(
            mapping.metadata["vehicle_type_id"],
            16,
        )

    def test_sync_es_idempotente_por_vehicle_key(self):
        vehicle = self._vehicle()

        self.catalog_client.vehicle_data.return_value = (
            vehicle,
        )

        first = ChubbVehicleCatalogSyncService.sync(
            provider_id=self.provider.id,
            vehicle_year=2024,
            catalog_client=self.catalog_client,
        )

        second = ChubbVehicleCatalogSyncService.sync(
            provider_id=self.provider.id,
            vehicle_year=2024,
            catalog_client=self.catalog_client,
        )

        self.assertEqual(
            Marca.objects.count(),
            1,
        )

        self.assertEqual(
            SubMarca.objects.count(),
            1,
        )

        self.assertEqual(
            VehiculoCatalogo.objects.count(),
            1,
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

    def test_sync_dos_vehicle_key_crean_dos_vehiculos(self):
        self.catalog_client.vehicle_data.return_value = (
            self._vehicle(
                vehicle_id=64,
                vehicle_key="01030100216",
            ),
            self._vehicle(
                vehicle_id=65,
                vehicle_key="01030100217",
            ),
        )

        result = ChubbVehicleCatalogSyncService.sync(
            provider_id=self.provider.id,
            vehicle_year=2024,
            catalog_client=self.catalog_client,
        )

        self.assertEqual(len(result), 2)

        self.assertEqual(
            VehiculoCatalogo.objects.count(),
            2,
        )

        self.assertEqual(
            ProviderCatalogMapping.objects.filter(
                provider=self.provider,
                catalog=self.catalog,
            ).count(),
            2,
        )

    def test_sync_ignora_vehiculos_inactivos(self):
        self.catalog_client.vehicle_data.return_value = (
            self._vehicle(
                active=False,
            ),
        )

        result = ChubbVehicleCatalogSyncService.sync(
            provider_id=self.provider.id,
            vehicle_year=2024,
            catalog_client=self.catalog_client,
        )

        self.assertEqual(result, ())

        self.assertFalse(
            VehiculoCatalogo.objects.exists()
        )

        self.assertFalse(
            ProviderCatalogMapping.objects.exists()
        )

    def test_sync_rechaza_anio_invalido_antes_de_http(self):
        with self.assertRaises(ValueError):
            ChubbVehicleCatalogSyncService.sync(
                provider_id=self.provider.id,
                vehicle_year=1900,
                catalog_client=self.catalog_client,
            )

        self.catalog_client.vehicle_data.assert_not_called()
