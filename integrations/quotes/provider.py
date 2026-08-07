from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import (
    InternalQuoteRequest,
    QuoteResult,
)


@runtime_checkable
class QuoteProvider(Protocol):
    """
    Contrato común para cualquier proveedor de cotizaciones.

    Cada implementación recibe el contrato interno del ERP y devuelve
    un resultado normalizado, sin exponer contratos específicos del
    proveedor.
    """

    provider_code: str

    def quote(
        self,
        request: InternalQuoteRequest,
    ) -> QuoteResult:
        """
        Ejecuta una cotización y devuelve un resultado normalizado.
        """
        ...
