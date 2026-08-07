from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from integrations.providers.contracts import (
    QuoteAmount,
    QuoteResponse,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
    ProviderQuoteError,
)

class ChubbQuoteResponseMapper:
    """
    Convierte la respuesta de POST /quote al contrato canónico
    QuoteResponse.

    No realiza llamadas HTTP.
    No consulta configuración.
    No consulta catálogos.
    """

    @classmethod
    def map(
        cls,
        *,
        provider_id: int,
        payload: Mapping[str, Any],
    ) -> QuoteResponse:
        cls._validate_provider_id(provider_id)

        if not isinstance(payload, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta de cotización de Chubb "
                "debe ser un objeto JSON."
            )

        if not payload.get("success", False):
            raise ProviderQuoteError(
                cls._build_failure_message(payload)
            )

        response_data = payload.get("responseData")

        if not isinstance(response_data, Mapping):
            raise ProviderInvalidResponseError(
                "La respuesta exitosa de Chubb no contiene "
                "'responseData' válido."
            )

        quote_id = cls._required_text(
            response_data.get("quoteId"),
            field_name="quoteId",
        )

        quote_version_id = cls._required_text(
            response_data.get("quoteVersionId"),
            field_name="quoteVersionId",
        )

        net_premium = cls._required_decimal(
            response_data.get("baseNetPremium"),
            field_name="baseNetPremium",
        )

        fees = cls._optional_decimal(
            response_data.get("feeAmount"),
            default=Decimal("0"),
        )

        taxes = cls._optional_decimal(
            response_data.get("taxAmount"),
            default=Decimal("0"),
        )

        total = cls._required_decimal(
            response_data.get("totalPremiumAmount"),
            field_name="totalPremiumAmount",
        )

        return QuoteResponse(
            provider_id=provider_id,
            provider_quote_id=quote_id,
            status="QUOTED",
            amount=QuoteAmount(
                net_premium=net_premium,
                taxes=taxes,
                fees=fees,
                total=total,
                currency="MXN",
            ),
            raw_response=dict(payload),
            metadata={
                "quote_version_id": quote_version_id,
                "base_net_premium_without_discount": (
                    cls._optional_decimal(
                        response_data.get(
                            "baseNetPremiumWithoutDiscount"
                        ),
                        default=None,
                    )
                ),
                "surcharge_amount": cls._optional_decimal(
                    response_data.get("surchargeAmount"),
                    default=Decimal("0"),
                ),
                "discounts": list(
                    response_data.get("discounts") or []
                ),
                "messages": list(
                    payload.get("messages") or []
                ),
            },
        )

    @classmethod
    def _build_failure_message(
        cls,
        payload: Mapping[str, Any],
    ) -> str:
        messages = payload.get("messages")

        if not messages:
            return (
                "Chubb indicó que la cotización no fue exitosa."
            )

        if not isinstance(messages, list):
            return (
                "Chubb rechazó la cotización. "
                f"Detalle: {messages}"
            )

        formatted_messages = []

        for message in messages:
            if isinstance(message, Mapping):
                text = (
                    message.get("message")
                    or message.get("description")
                    or message.get("error")
                    or str(message)
                )

                code = message.get("messageCode")

                if code is not None:
                    formatted_messages.append(
                        f"[{code}] {text}"
                    )
                else:
                    formatted_messages.append(str(text))
            else:
                formatted_messages.append(str(message))

        detail = "; ".join(formatted_messages)

        return (
            "Chubb rechazó la cotización."
            + (f" Detalle: {detail}" if detail else "")
        )

    @staticmethod
    def _required_decimal(
        value: Any,
        *,
        field_name: str,
    ) -> Decimal:
        if value is None or value == "":
            raise ProviderInvalidResponseError(
                f"La respuesta de Chubb no contiene "
                f"'{field_name}'."
            )

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                f"La respuesta de Chubb contiene "
                f"'{field_name}' inválido."
            ) from exc

    @staticmethod
    def _optional_decimal(
        value: Any,
        *,
        default: Decimal | None,
    ) -> Decimal | None:
        if value is None or value == "":
            return default

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    @staticmethod
    def _required_text(
        value: Any,
        *,
        field_name: str,
    ) -> str:
        if value is None:
            raise ProviderInvalidResponseError(
                f"La respuesta de Chubb no contiene "
                f"'{field_name}'."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ProviderInvalidResponseError(
                f"La respuesta de Chubb contiene "
                f"'{field_name}' vacío."
            )

        return normalized

    @staticmethod
    def _validate_provider_id(
        provider_id: int,
    ) -> None:
        if not isinstance(provider_id, int) or provider_id <= 0:
            raise ValueError(
                "provider_id debe ser un entero mayor que cero."
            )
        