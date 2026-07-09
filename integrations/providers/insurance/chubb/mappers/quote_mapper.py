from decimal import Decimal

from integrations.broker.contracts import (
    BrokerQuoteResult,
    BrokerQuoteOption,
)


class ChubbQuoteMapper:
    """
    Convierte la respuesta de cotización de la API de Chubb al modelo de dominio del Broker.

    Transforma el JSON recibido del endpoint POST /quote en un BrokerQuoteResult,
    incluyendo las opciones de cotización, primas y errores cuando existan.

    Responsabilidades:
    - Interpretar la respuesta de Chubb.
    - Crear objetos BrokerQuoteOption.
    - Construir un BrokerQuoteResult uniforme para el Insurance Broker.

    No realiza llamadas HTTP.
    No construye payloads.
    No conoce modelos Django.
    No contiene lógica de negocio.

    Quote Builder → BrokerQuoteRequest → JSON Chubb
    API Client → JSON → REST API
    Quote Mapper → JSON Chubb → BrokerQuoteResult

    """

    def map(self, request, response) -> BrokerQuoteResult:
        result = BrokerQuoteResult(request=request)

        if not isinstance(response, dict):
            result.errors.append({
                "provider": "CHUBB",
                "error": "Respuesta Chubb inválida o no esperada.",
                "raw": response,
            })
            return result

        message = response.get("message")
        if message:
            result.errors.append({
                "provider": "CHUBB",
                "error": message,
                "code": response.get("messageCode"),
                "type": response.get("messageType"),
            })

        option = BrokerQuoteOption(
            provider="CHUBB",
            provider_quote_id=self._quote_id(response),
            product_name="Chubb Auto",
            package_name=self._package_name(response),
            prima_total=self._decimal(response.get("totalPremiumAmount")),
            prima_neta=self._decimal(response.get("baseNetPremiumWithoutDiscount")),
            derechos=self._decimal(response.get("feeAmount")),
            iva=self._decimal(response.get("taxAmount")),
            recargos=self._decimal(response.get("surchargeAmount")),
            raw_response=response,
        )

        if option.prima_total > Decimal("0.00"):
            result.options.append(option)

        return result

    def _quote_id(self, response) -> str | None:
        quote_id = response.get("quoteId")
        quote_version_id = response.get("quoteVersionId")

        if quote_id and quote_version_id:
            return f"{quote_id}:{quote_version_id}"

        if quote_id:
            return str(quote_id)

        return None

    def _package_name(self, response) -> str | None:
        items = response.get("items") or []

        if not items:
            return None

        packages = items[0].get("packages") or []

        if not packages:
            return None

        package = packages[0]

        package_id = package.get("packageId")

        if package_id:
            return f"Paquete {package_id}"

        return None

    def _decimal(self, value) -> Decimal:
        if value in (None, ""):
            return Decimal("0.00")

        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0.00")
