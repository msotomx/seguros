from integrations.catalog.contracts import (
    CatalogValue,
    ProviderCatalogValue,
)
from integrations.catalog.exceptions import (
    CatalogItemNotFoundError,
    CatalogNotFoundError,
    ProviderCatalogMappingNotFoundError,
)
from integrations.models import (
    Catalog,
    CatalogItem,
    ProviderCatalogMapping,
)


class DjangoCatalogRepository:
    """
    Implementación del CatalogRepository mediante Django ORM.
    """

    def get_item(
        self,
        *,
        catalog_code: str,
        internal_code: str,
    ) -> CatalogValue:
        self._ensure_catalog_exists(catalog_code)

        try:
            item = (
                CatalogItem.objects
                .select_related("catalog")
                .get(
                    catalog__code=catalog_code,
                    catalog__is_active=True,
                    code=internal_code,
                    is_active=True,
                )
            )
        except CatalogItem.DoesNotExist as exc:
            raise CatalogItemNotFoundError(
                f"No existe el elemento activo "
                f"'{catalog_code}:{internal_code}'."
            ) from exc

        return self._to_catalog_value(item)

    def list_items(
        self,
        *,
        catalog_code: str,
    ) -> tuple[CatalogValue, ...]:
        self._ensure_catalog_exists(catalog_code)

        items = (
            CatalogItem.objects
            .select_related("catalog")
            .filter(
                catalog__code=catalog_code,
                catalog__is_active=True,
                is_active=True,
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

        return tuple(
            self._to_catalog_value(item)
            for item in items
        )

    def to_provider(
        self,
        *,
        provider_id: int,
        catalog_code: str,
        internal_code: str,
    ) -> ProviderCatalogValue:
        try:
            mapping = (
                ProviderCatalogMapping.objects
                .select_related(
                    "provider",
                    "catalog",
                    "catalog_item",
                )
                .get(
                    provider_id=provider_id,
                    catalog__code=catalog_code,
                    catalog__is_active=True,
                    catalog_item__code=internal_code,
                    catalog_item__is_active=True,
                    is_active=True,
                )
            )
        except ProviderCatalogMapping.DoesNotExist as exc:
            raise ProviderCatalogMappingNotFoundError(
                f"No existe un mapeo activo para provider={provider_id}, "
                f"catálogo='{catalog_code}' y "
                f"código interno='{internal_code}'."
            ) from exc

        return self._to_provider_catalog_value(mapping)

    def from_provider(
        self,
        *,
        provider_id: int,
        catalog_code: str,
        external_code: str,
    ) -> ProviderCatalogValue:
        try:
            mapping = (
                ProviderCatalogMapping.objects
                .select_related(
                    "provider",
                    "catalog",
                    "catalog_item",
                )
                .get(
                    provider_id=provider_id,
                    catalog__code=catalog_code,
                    catalog__is_active=True,
                    catalog_item__is_active=True,
                    external_code=external_code,
                    is_active=True,
                )
            )
        except ProviderCatalogMapping.DoesNotExist as exc:
            raise ProviderCatalogMappingNotFoundError(
                f"No existe un mapeo activo para provider={provider_id}, "
                f"catálogo='{catalog_code}' y "
                f"código externo='{external_code}'."
            ) from exc

        return self._to_provider_catalog_value(mapping)

    def _ensure_catalog_exists(
        self,
        catalog_code: str,
    ) -> None:
        exists = Catalog.objects.filter(
            code=catalog_code,
            is_active=True,
        ).exists()

        if not exists:
            raise CatalogNotFoundError(
                f"No existe el catálogo activo '{catalog_code}'."
            )

    @staticmethod
    def _to_catalog_value(
        item: CatalogItem,
    ) -> CatalogValue:
        return CatalogValue(
            catalog_code=item.catalog.code,
            internal_code=item.code,
            name=item.name,
            metadata=dict(item.metadata or {}),
        )

    @staticmethod
    def _to_provider_catalog_value(
        mapping: ProviderCatalogMapping,
    ) -> ProviderCatalogValue:
        return ProviderCatalogValue(
            provider_id=mapping.provider_id,
            catalog_code=mapping.catalog.code,
            internal_code=mapping.catalog_item.code,
            internal_name=mapping.catalog_item.name,
            external_code=mapping.external_code,
            external_name=mapping.external_name,
            metadata=dict(mapping.metadata or {}),
        )
    