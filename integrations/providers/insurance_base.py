# proveedores externos Chubb, Qualitas, GNP, etc
# Cotización y emisión de seguros

from abc import ABC, abstractmethod
from typing import Any

from integrations.catalog import CatalogService
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.contracts import (
    QuoteRequest,
    QuoteResponse,
)
from integrations.providers.exceptions import (
    ProviderUnsupportedOperationError,
)


class BaseInsuranceProviderAdapter(ABC):
    """
    Base común para adapters de aseguradoras.

    Está orientada a operaciones salientes:
    cotización, emisión, cancelación y descarga de documentos.

    No procesa webhooks.
    """

    provider_code: str = ""
    supported_operations: frozenset[str] = frozenset()

    def __init__(
        self,
        *,
        configuration_service: Any = ProviderConfigurationService,
        catalog_service: Any = CatalogService,
    ):
        self.configuration_service = configuration_service
        self.catalog_service = catalog_service

    def supports(
        self,
        operation: str,
    ) -> bool:
        normalized = self._normalize_operation(operation)
        return normalized in self.supported_operations

    def ensure_supported(
        self,
        operation: str,
    ) -> None:
        normalized = self._normalize_operation(operation)

        if normalized not in self.supported_operations:
            raise ProviderUnsupportedOperationError(
                f"El provider '{self.provider_code}' "
                f"no soporta la operación '{operation}'."
            )

    @staticmethod
    def _normalize_operation(
        operation: str,
    ) -> str:
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError(
                "La operación no puede estar vacía."
            )

        return operation.strip().lower()

    @abstractmethod
    def authenticate(self) -> None:
        """Obtiene o prepara la autenticación del provider."""

    @abstractmethod
    def quote(
        self,
        *,
        request: QuoteRequest,
    ) -> QuoteResponse:
        """Genera una cotización con la aseguradora."""
        