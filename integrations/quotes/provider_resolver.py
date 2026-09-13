from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from integrations.quotes.provider import QuoteProvider


class QuoteProviderBuilder(Protocol):
    provider_code: str

    def build(
        self,
        *,
        ambiente: str,
        ramo: str,
    ) -> QuoteProvider:
        ...


class QuoteProviderResolver:
    """
    Composition root de providers de cotización.

    Conoce qué builder corresponde a cada implementación,
    pero no contiene configuración operativa del proveedor.

    grouping_id, rate_id, credenciales, producto, etc.
    siguen proviniendo de ProviderConfiguration.
    """

    def __init__(
        self,
        *,
        builders: Mapping[
            str,
            QuoteProviderBuilder,
        ],
    ) -> None:
        normalized: dict[
            str,
            QuoteProviderBuilder,
        ] = {}

        for provider_code, builder in builders.items():
            code = self._normalize_code(
                provider_code
            )

            if code in normalized:
                raise ValueError(
                    "Existe más de un builder para "
                    f"provider={code}."
                )

            normalized[code] = builder

        if not normalized:
            raise ValueError(
                "Debe registrarse al menos un "
                "QuoteProviderBuilder."
            )

        self._builders = normalized

    def build(
        self,
        *,
        provider_code: str,
        ambiente: str,
        ramo: str,
    ) -> QuoteProvider:
        code = self._normalize_code(
            provider_code
        )

        try:
            builder = self._builders[code]
        except KeyError as exc:
            raise ValueError(
                "No existe builder de cotización "
                f"para provider={code}."
            ) from exc

        provider = builder.build(
            ambiente=ambiente,
            ramo=ramo,
        )

        returned_code = self._normalize_code(
            provider.provider_code
        )

        if returned_code != code:
            raise ValueError(
                "El builder devolvió un provider "
                "con código distinto al solicitado."
            )

        return provider

    @staticmethod
    def _normalize_code(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "provider_code debe ser una cadena."
            )

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                "provider_code no puede estar vacío."
            )

        return normalized
