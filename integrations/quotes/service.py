from __future__ import annotations

from collections.abc import Iterable, Mapping
from time import perf_counter
from typing import Any

from integrations.quotes.contracts import (
    QuoteAttempt,
    QuoteBatchResult,
    QuoteProviderError,
    InternalQuoteRequest,
)
from integrations.quotes.provider import QuoteProvider


class QuoteService:
    """
    Orquesta la ejecución de cotizaciones con uno o varios proveedores.
    """

    def __init__(
        self,
        providers: Iterable[QuoteProvider],
    ) -> None:
        provider_map: dict[str, QuoteProvider] = {}

        for provider in providers:
            provider_code = self._normalize_provider_code(
                provider.provider_code
            )

            if provider_code in provider_map:
                raise ValueError(
                    "Existe más de un proveedor registrado con el "
                    f"código {provider_code}."
                )

            provider_map[provider_code] = provider

        if not provider_map:
            raise ValueError(
                "QuoteService requiere al menos un proveedor."
            )

        self._providers = provider_map

    @property
    def provider_codes(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())

    def quote_one(
        self,
        provider_code: str,
        request: InternalQuoteRequest,
    ) -> QuoteAttempt:
        """
        Ejecuta un solo proveedor.

        Los errores se convierten en QuoteAttempt fallido y no se
        propagan fuera del servicio.
        """

        normalized_code = self._normalize_provider_code(
            provider_code
        )

        provider = self._providers.get(normalized_code)

        if provider is None:
            raise ValueError(
                f"El proveedor {normalized_code} no está registrado."
            )

        started_at = perf_counter()

        try:
            result = provider.quote(request)
        except Exception as exc:
            elapsed_ms = self._elapsed_ms(started_at)

            return QuoteAttempt(
                provider_code=normalized_code,
                success=False,
                elapsed_ms=elapsed_ms,
                error=QuoteProviderError(
                    provider_code=normalized_code,
                    message=str(exc) or exc.__class__.__name__,
                    error_type=exc.__class__.__name__,
                    retryable=self._is_retryable(exc),
                ),
            )

        elapsed_ms = self._elapsed_ms(started_at)

        if result.provider_code != normalized_code:
            raise ValueError(
                "El proveedor devolvió un provider_code distinto "
                "al registrado. "
                f"Esperado={normalized_code}, "
                f"recibido={result.provider_code}."
            )

        return QuoteAttempt(
            provider_code=normalized_code,
            success=True,
            elapsed_ms=elapsed_ms,
            result=result,
        )

    def quote_many(
        self,
        requests: Mapping[str, InternalQuoteRequest],
        *,
        fail_fast: bool = False,
    ) -> QuoteBatchResult:
    
        """
        Ejecuta varios proveedores.

        `requests` utiliza el código del proveedor como llave:

        {
            "CHUBB": chubb_request,
            "QUALITAS": qualitas_request,
        }
        """

        if not requests:
            raise ValueError(
                "Debe proporcionarse al menos una solicitud."
            )

        attempts: list[QuoteAttempt] = []

        for provider_code, request in requests.items():
            attempt = self.quote_one(
                provider_code,
                request,
            )

            attempts.append(attempt)

            if fail_fast and not attempt.success:
                break

        return QuoteBatchResult(
            attempts=tuple(attempts),
        )

    @staticmethod
    def _normalize_provider_code(
        provider_code: str,
    ) -> str:
        if not isinstance(provider_code, str):
            raise TypeError(
                "provider_code debe ser una cadena."
            )

        normalized = provider_code.strip().upper()

        if not normalized:
            raise ValueError(
                "provider_code no puede estar vacío."
            )

        return normalized

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> int:
        elapsed = perf_counter() - started_at

        return max(
            0,
            round(elapsed * 1000),
        )

    @staticmethod
    def _is_retryable(
        exc: Exception,
    ) -> bool:
        """
        Primera aproximación.

        Después podremos determinarlo usando las excepciones específicas
        del proveedor: timeout, conexión, HTTP 429 y HTTP 5xx.
        """

        error_name = exc.__class__.__name__.lower()

        retryable_fragments = (
            "timeout",
            "connection",
            "temporarily",
            "ratelimit",
            "rate_limit",
        )

        return any(
            fragment in error_name
            for fragment in retryable_fragments
        )
