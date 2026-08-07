class CatalogError(Exception):
    """Error base del Catalog Engine."""


class CatalogNotFoundError(CatalogError):
    """El catálogo solicitado no existe o está inactivo."""


class CatalogItemNotFoundError(CatalogError):
    """El elemento canónico no existe o está inactivo."""


class ProviderCatalogMappingNotFoundError(CatalogError):
    """No existe un mapeo activo para el provider solicitado."""
    