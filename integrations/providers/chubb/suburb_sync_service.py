from integrations.catalog.suburb_code_service import (
    SuburbCodeService,
)

from integrations.catalog.mapping_write_service import (
    CatalogMappingWriteService,
)


class ChubbSuburbSyncService:
    CATALOG_CODE = "SUBURB"

    @classmethod
    def sync(
        cls,
        *,
        provider_id: int,
        zip_code: str,
        catalog_client,
        mapping_write_service=CatalogMappingWriteService,
    ) -> tuple:
        zip_code = cls._normalize_zip_code(
            zip_code
        )

        suburbs = catalog_client.suburbs(
            zip_code=zip_code,
        )

        mappings = []

        for suburb in suburbs:
            internal_code = SuburbCodeService.build(
                zip_code=zip_code,
                name=suburb.name,
            )

            metadata = {
                "zip_code": zip_code,
            }

            if suburb.country_subdivision_id is not None:
                metadata[
                    "country_subdivision_id"
                ] = suburb.country_subdivision_id

            if suburb.municipality_id is not None:
                metadata[
                    "municipality_id"
                ] = suburb.municipality_id

            if suburb.population_id is not None:
                metadata[
                    "population_id"
                ] = suburb.population_id

            mapping = mapping_write_service.upsert(
                provider_id=provider_id,
                catalog_code=cls.CATALOG_CODE,
                internal_code=internal_code,
                internal_name=suburb.name,
                external_code=suburb.suburb_id,
                external_name=suburb.name,
                metadata=metadata,
            )

            mappings.append(mapping)

        return tuple(mappings)

    @staticmethod
    def _normalize_zip_code(
        value: str,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "zip_code no puede estar vacío."
            )

        return value.strip()

