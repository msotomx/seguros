from integrations.catalog.contracts import (
    CatalogRepository,
    CatalogValue,
    ProviderCatalogValue,
)
from integrations.catalog.django_repository import (
    DjangoCatalogRepository,
)


class CatalogService:
    """
    Punto público de entrada al Catalog Engine.

    Normaliza los datos de entrada y delega el acceso a datos
    a una implementación de CatalogRepository.
    """

    @classmethod
    def get_item(
        cls,
        *,
        catalog_code: str,
        internal_code: str,
        repository: CatalogRepository | None = None,
    ) -> CatalogValue:
        repo = cls._get_repository(repository)

        return repo.get_item(
            catalog_code=cls._normalize_code(catalog_code),
            internal_code=cls._normalize_code(internal_code),
        )

    @classmethod
    def list_items(
        cls,
        *,
        catalog_code: str,
        repository: CatalogRepository | None = None,
    ) -> tuple[CatalogValue, ...]:
        repo = cls._get_repository(repository)

        return repo.list_items(
            catalog_code=cls._normalize_code(catalog_code),
        )

    @classmethod
    def to_provider(
        cls,
        *,
        provider_id: int,
        catalog_code: str,
        internal_code: str,
        repository: CatalogRepository | None = None,
    ) -> ProviderCatalogValue:
        """
        Convierte un código canónico de Switchh al código externo
        utilizado por un provider.

        Ejemplo:
            PARTICULAR -> 01
        """

        repo = cls._get_repository(repository)

        return repo.to_provider(
            provider_id=cls._normalize_provider_id(provider_id),
            catalog_code=cls._normalize_code(catalog_code),
            internal_code=cls._normalize_code(internal_code),
        )

    @classmethod
    def from_provider(
        cls,
        *,
        provider_id: int,
        catalog_code: str,
        external_code: str,
        repository: CatalogRepository | None = None,
    ) -> ProviderCatalogValue:
        """
        Convierte un código externo del provider al código canónico
        utilizado por Switchh.

        Ejemplo:
            01 -> PARTICULAR
        """

        repo = cls._get_repository(repository)

        return repo.from_provider(
            provider_id=cls._normalize_provider_id(provider_id),
            catalog_code=cls._normalize_code(catalog_code),
            external_code=cls._normalize_external_code(
                external_code
            ),
        )

    @staticmethod
    def _get_repository(
        repository: CatalogRepository | None,
    ) -> CatalogRepository:
        if repository is not None:
            return repository

        return DjangoCatalogRepository()

    @staticmethod
    def _normalize_provider_id(value: int) -> int:
        try:
            provider_id = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "provider_id debe ser un número entero válido."
            ) from exc

        if provider_id <= 0:
            raise ValueError(
                "provider_id debe ser mayor que cero."
            )

        return provider_id

    @staticmethod
    def _normalize_code(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "El código no puede estar vacío."
            )

        return value.strip().upper()

    @staticmethod
    def _normalize_external_code(value: str) -> str:
        if value is None:
            raise ValueError(
                "El código externo no puede estar vacío."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ValueError(
                "El código externo no puede estar vacío."
            )

        return normalized
        