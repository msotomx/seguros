from __future__ import annotations

import unicodedata

from django.db import transaction

from integrations.catalog.mapping_write_service import (
    CatalogMappingWriteService,
)
from integrations.models import (
    AseguradoraConfiguracion,
    ProviderCatalogMapping,
)


class ChubbMunicipalitySyncService:
    CATALOG_CODE = "MUNICIPALITY"
    STATE_CATALOG_CODE = "STATE"

    @classmethod
    @transaction.atomic
    def sync(
        cls,
        *,
        provider_id: int,
        state_internal_code: str,
        catalog_client,
        mapping_write_service=CatalogMappingWriteService,
    ) -> tuple[ProviderCatalogMapping, ...]:
        state_internal_code = cls._normalize_code(
            state_internal_code
        )

        provider = AseguradoraConfiguracion.objects.get(
            pk=provider_id,
        )

        state_mapping = (
            ProviderCatalogMapping.objects
            .select_related(
                "catalog",
                "catalog_item",
            )
            .filter(
                provider_id=provider_id,
                catalog__code=cls.STATE_CATALOG_CODE,
                catalog__is_active=True,
                catalog_item__code=state_internal_code,
                catalog_item__is_active=True,
                is_active=True,
            )
            .first()
        )

        if state_mapping is None:
            raise ValueError(
                "No existe un mapping activo de STATE "
                f"para '{state_internal_code}' "
                f"y provider={provider_id}."
            )

        country_subdivision_id = (
            cls._positive_int(
                state_mapping.external_code,
                field_name="country_subdivision_id",
            )
        )

        municipalities = catalog_client.municipalities(
            country_subdivision_id=country_subdivision_id,
            business_profile_name=(
                provider.business_profile_name
            ),
            grouping_id=provider.grouping_id,
            rate_id=provider.rate_id,
        )

        mappings: list[ProviderCatalogMapping] = []

        for municipality in municipalities:
            internal_code = cls._normalize_code(
                municipality.name
            )

            mapping = mapping_write_service.upsert(
                provider_id=provider_id,
                catalog_code=cls.CATALOG_CODE,
                internal_code=internal_code,
                internal_name=municipality.name.strip(),
                external_code=municipality.municipality_id,
                external_name=municipality.name.strip(),
                metadata={
                    "state_internal_code": (
                        state_internal_code
                    ),
                },
                mapping_metadata={
                    "country_subdivision_id": (
                        country_subdivision_id
                    ),
                },
            )

            mappings.append(mapping)

        return tuple(mappings)

    @staticmethod
    def _normalize_code(value: str) -> str:
        value = str(value or "").strip()

        if not value:
            raise ValueError(
                "El código interno no puede estar vacío."
            )

        normalized = unicodedata.normalize(
            "NFKD",
            value,
        )

        normalized = "".join(
            char
            for char in normalized
            if not unicodedata.combining(char)
        )

        return " ".join(
            normalized.upper().split()
        )

    @staticmethod
    def _positive_int(
        value,
        *,
        field_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} debe ser entero positivo."
            )

        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field_name} debe ser entero positivo."
            ) from exc

        if normalized <= 0:
            raise ValueError(
                f"{field_name} debe ser entero positivo."
            )

        return normalized
