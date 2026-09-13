from django.db import transaction

from integrations.models import (
    AseguradoraConfiguracion,
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)


class CatalogMappingWriteService:
    """
    Servicio genérico de escritura de equivalencias entre
    catálogos canónicos y valores externos de un provider.

    No contiene conocimiento de Chubb ni de ningún catálogo
    específico.
    """

    @classmethod
    @transaction.atomic
    def upsert(
        cls,
        *,
        provider_id: int,
        catalog_code: str,
        internal_code: str,
        internal_name: str,
        external_code: str,
        external_name: str = "",
        metadata: dict | None = None,
        mapping_metadata: dict | None = None,
    ) -> ProviderCatalogMapping:
        provider = AseguradoraConfiguracion.objects.get(
            pk=provider_id,
        )

        catalog = Catalog.objects.get(
            code=cls._normalize_code(catalog_code),
            is_active=True,
        )

        item, _ = CatalogItem.objects.update_or_create(
            catalog=catalog,
            code=cls._normalize_code(internal_code),
            defaults={
                "name": cls._required_text(
                    internal_name,
                    "internal_name",
                ),
                "metadata": dict(metadata or {}),
                "is_active": True,
            },
        )

        mapping, _ = (
            ProviderCatalogMapping.objects.update_or_create(
                provider=provider,
                catalog_item=item,
                defaults={
                    "catalog": catalog,
                    "external_code": cls._external_code(
                        external_code
                    ),
                    "external_name": (
                        str(external_name).strip()
                        if external_name is not None
                        else ""
                    ),
                    "metadata": dict(
                        mapping_metadata or {}
                    ),
                    "is_active": True,
                },
            )
        )

        return mapping

    @staticmethod
    def _normalize_code(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "El código no puede estar vacío."
            )

        return value.strip().upper()

    @staticmethod
    def _required_text(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} no puede estar vacío."
            )

        return value.strip()

    @staticmethod
    def _external_code(value: object) -> str:
        if value is None:
            raise ValueError(
                "external_code no puede estar vacío."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ValueError(
                "external_code no puede estar vacío."
            )

        return normalized
