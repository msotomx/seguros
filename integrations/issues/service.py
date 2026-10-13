from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter

from integrations.issues.contracts import (
    InternalIssueRequest,
    IssueAttempt,
    IssueProviderError,
)
from integrations.issues.provider import IssueProvider


class IssueService:
    """
    Orquesta la emisión con un proveedor.
    """

    def __init__(
        self,
        providers: Iterable[IssueProvider],
    ) -> None:
        provider_map: dict[str, IssueProvider] = {}

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
                "IssueService requiere al menos un proveedor."
            )

        self._providers = provider_map

    @property
    def provider_codes(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())

    def issue_one(
        self,
        provider_code: str,
        request: InternalIssueRequest,
    ) -> IssueAttempt:

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
            result = provider.issue(request)
        except Exception as exc:
            elapsed_ms = self._elapsed_ms(started_at)

            return IssueAttempt(
                provider_code=normalized_code,
                success=False,
                elapsed_ms=elapsed_ms,
                error=IssueProviderError(
                    provider_code=normalized_code,
                    message=str(exc) or exc.__class__.__name__,
                    error_type=exc.__class__.__name__,
                    retryable=self._is_retryable(exc),
                    outcome_unknown=self._is_outcome_unknown(exc),
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

        return IssueAttempt(
            provider_code=normalized_code,
            success=True,
            elapsed_ms=elapsed_ms,
            result=result,
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

    @staticmethod
    def _is_outcome_unknown(
        exc: Exception,
    ) -> bool:
        error_name = exc.__class__.__name__.lower()

        unknown_fragments = (
            "timeout",
            "connection",
        )

        return any(
            fragment in error_name
            for fragment in unknown_fragments
        )
