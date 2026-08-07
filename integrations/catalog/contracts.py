from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class CatalogValue:
    catalog_code: str
    internal_code: str
    name: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ProviderCatalogValue:
    provider_id: int
    catalog_code: str
    internal_code: str
    internal_name: str
    external_code: str
    external_name: str
    metadata: Mapping[str, Any]


class CatalogRepository(Protocol):

    def get_item(
        self,
        *,
        catalog_code: str,
        internal_code: str,
    ) -> CatalogValue:
        ...

    def list_items(
        self,
        *,
        catalog_code: str,
    ) -> tuple[CatalogValue, ...]:
        ...

    def to_provider(
        self,
        *,
        provider_id: int,
        catalog_code: str,
        internal_code: str,
    ) -> ProviderCatalogValue:
        ...

    def from_provider(
        self,
        *,
        provider_id: int,
        catalog_code: str,
        external_code: str,
    ) -> ProviderCatalogValue:
        ...
