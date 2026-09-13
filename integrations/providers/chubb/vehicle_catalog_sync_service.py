from django.db import transaction

from autos.models import Marca, SubMarca, VehiculoCatalogo
from integrations.catalog.mapping_write_service import (
    CatalogMappingWriteService,
)
from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    ProviderCatalogMapping,
)


class ChubbVehicleCatalogSyncService:
    CATALOG_CODE = "VEHICLE"

    @classmethod
    @transaction.atomic
    def sync(
        cls,
        *,
        provider_id: int,
        vehicle_year: int,
        catalog_client,
        mapping_write_service=CatalogMappingWriteService,
    ) -> tuple[ProviderCatalogMapping, ...]:
        if not isinstance(vehicle_year, int) or isinstance(
            vehicle_year,
            bool,
        ):
            raise ValueError(
                "vehicle_year debe ser un entero."
            )

        if vehicle_year < 1950 or vehicle_year > 2100:
            raise ValueError(
                "vehicle_year está fuera del rango permitido."
            )

        provider = AseguradoraConfiguracion.objects.get(
            pk=provider_id,
        )

        catalog = Catalog.objects.get(
            code=cls.CATALOG_CODE,
            is_active=True,
        )

        vehicles = catalog_client.vehicle_data(
            business_profile_name=provider.business_profile_name,
            grouping_id=provider.grouping_id,
            rate_id=provider.rate_id,
            vehicle_year=vehicle_year,
        )

        mappings: list[ProviderCatalogMapping] = []

        for vehicle in vehicles:
            if not vehicle.active:
                continue

            vehicle_key = vehicle.vehicle_key.strip()

            existing_mapping = (
                ProviderCatalogMapping.objects
                .filter(
                    provider_id=provider_id,
                    catalog=catalog,
                    external_code=vehicle_key,
                    is_active=True,
                )
                .first()
            )

            if existing_mapping is not None:
                mappings.append(existing_mapping)
                continue

            marca = cls._get_or_create_marca(
                vehicle.make_description
            )

            submarca = cls._get_or_create_submarca(
                marca=marca,
                name=vehicle.submake_description,
            )

            vehiculo_catalogo = VehiculoCatalogo.objects.create(
                marca=marca,
                submarca=submarca,
                anio=vehicle_year,
                version=vehicle.short_description.strip(),
                tipo_vehiculo=(
                    vehicle.vehicle_type_description.strip()
                ),
            )

            internal_code = (
                f"VEHICULO_CATALOGO_{vehiculo_catalogo.pk}"
            )

            mapping = mapping_write_service.upsert(
                provider_id=provider_id,
                catalog_code=cls.CATALOG_CODE,
                internal_code=internal_code,
                internal_name=cls._internal_name(
                    vehicle=vehicle,
                    vehicle_year=vehicle_year,
                ),
                external_code=vehicle_key,
                external_name=vehicle.short_description.strip(),
                metadata={
                    "vehiculo_catalogo_id": (
                        vehiculo_catalogo.pk
                    ),
                    "vehicle_year": vehicle_year,
                },
                mapping_metadata={
                    "vehicle_id": vehicle.vehicle_id,
                    "make_id": vehicle.make_id,
                    "submake_id": vehicle.submake_id,
                    "vehicle_type_id": (
                        vehicle.vehicle_type_id
                    ),
                    "vehicle_description": (
                        vehicle.description
                    ),
                    "short_description": (
                        vehicle.short_description
                    ),
                    "long_description": (
                        vehicle.long_description
                    ),
                    "cmst": vehicle.cmst,
                    "mtc": vehicle.mtc,
                    "passengers": vehicle.passengers,
                    "tonnage": vehicle.tonnage,
                    "vehicle_group_id": (
                        vehicle.vehicle_group_id
                    ),
                    "vehicle_group_description": (
                        vehicle.vehicle_group_description
                    ),
                    "status": vehicle.status,
                    "status_description": (
                        vehicle.status_description
                    ),
                    "vehicle_condition_id": (
                        vehicle.vehicle_condition_id
                    ),
                },
            )

            mappings.append(mapping)

        return tuple(mappings)

    @staticmethod
    def _get_or_create_marca(
        name: str,
    ) -> Marca:
        name = name.strip()

        marca = (
            Marca.objects
            .filter(nombre__iexact=name)
            .first()
        )

        if marca is not None:
            return marca

        return Marca.objects.create(
            nombre=name,
        )

    @staticmethod
    def _get_or_create_submarca(
        *,
        marca: Marca,
        name: str,
    ) -> SubMarca:
        name = name.strip()

        submarca = (
            SubMarca.objects
            .filter(
                marca=marca,
                nombre__iexact=name,
            )
            .first()
        )

        if submarca is not None:
            return submarca

        return SubMarca.objects.create(
            marca=marca,
            nombre=name,
        )

    @staticmethod
    def _internal_name(
        *,
        vehicle,
        vehicle_year: int,
    ) -> str:
        return (
            f"{vehicle.make_description.strip()} "
            f"{vehicle.vehicle_type_description.strip()} "
            f"{vehicle.short_description.strip()} "
            f"{vehicle_year}"
        ).strip()
