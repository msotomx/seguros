"""
integrations/providers/insurance/chubb/builders/quote_builder.py

Construye el payload de cotización requerido por la API de Chubb.

Convierte un BrokerQuoteRequest y la configuración del Provider
(AseguradoraConfiguracion) en el JSON esperado por el endpoint POST /quote.

Responsabilidades:
- Validar la información mínima requerida.
- Construir el payload conforme a la especificación de Chubb.
- Mantener aislado el formato de la API respecto al Broker.

No realiza llamadas HTTP.
No interpreta respuestas.
No conoce modelos Django.
"""

from integrations.broker.contracts import BrokerQuoteRequest


class ChubbQuoteBuilder:
    """
    Construye el payload requerido por Chubb para POST /quote.

    Responsabilidad:
    BrokerQuoteRequest + provider_config -> JSON Chubb

    No llama APIs.
    No interpreta respuestas.
    No conoce modelos Django.
    """

    def build(self, request: BrokerQuoteRequest, provider_config) -> dict:
        self._validate_request(request)
        self._validate_config(provider_config)

        return {
            "quoteId": 0,
            "quoteVersionId": 0,
            "quoteType": 0,
            "DatosGenerales": self._general_data(request, provider_config),
            "items": [
                self._item(request, provider_config),
            ],
        }

    def _general_data(self, request: BrokerQuoteRequest, provider_config) -> dict:
        return {
            "productId": provider_config.product_id,
            "businessprofileId": provider_config.businessprofile_id,
            "agentId": provider_config.agent_id,
            "conduitId": provider_config.conduit_id,
            "groupingId": provider_config.grouping_id,
            "rateId": provider_config.rate_id,
            "effectiveDate": request.vigencia_desde.isoformat(),
            "expirationDate": request.vigencia_hasta.isoformat(),
            "calculationTypeId": provider_config.calculation_type_id,
            "currencyId": getattr(provider_config, "currency_id", 1),
            "reference": f"SWITCHH-{request.cotizacion_id}",
            "prospectName": request.cliente.nombre,
            "paymentTypes": [
                {
                    "paymentTypeId": provider_config.payment_type_id,
                }
            ],
        }

    def _item(self, request: BrokerQuoteRequest, provider_config) -> dict:
        return {
            "quoteVersionId": 0,
            "riskId": 0,
            "riskNumber": 0,
            "discount": {
                "discountTypeId": getattr(provider_config, "discount_type_id", 1),
                "discountPercentage": getattr(provider_config, "discount_percentage", 0),
            },
            "vehicle": self._vehicle(request, provider_config),
            "packages": self._packages(provider_config),
            "coverages": [],
        }

    def _vehicle(self, request: BrokerQuoteRequest, provider_config) -> dict:
        return {
            "vehicleKey": provider_config.vehicle_key,
            "vehicleId": provider_config.vehicle_id,
            "vehiculeCustomDescription": self._vehicle_description(request),
            "insuredAmountTypeId": provider_config.insured_amount_type_id,
            "deductibleTypeId": getattr(provider_config, "deductible_type_id", 0),
            "year": request.vehiculo.anio,
            "plate": request.vehiculo.placas or "",
            "vin": request.vehiculo.vin or "",
            "countrySubdivisionId": provider_config.country_subdivision_id,
            "municipalityId": provider_config.municipality_id,
            "zipCode": self._zip_code(request),
            "useId": provider_config.use_id,
            "garageUse": False,
            "nadasc": False,
            "genderId": 2,
        }

    def _packages(self, provider_config) -> list[dict]:
        return [
            {
                "packageId": provider_config.package_id,
                "selected": True,
            }
        ]

    def _vehicle_description(self, request: BrokerQuoteRequest) -> str:
        parts = [
            request.vehiculo.marca,
            request.vehiculo.submarca,
            request.vehiculo.version,
            str(request.vehiculo.anio) if request.vehiculo.anio else None,
        ]

        return " ".join([str(part) for part in parts if part])

    def _zip_code(self, request: BrokerQuoteRequest) -> int | None:
        zip_code = request.vehiculo.codigo_postal or request.cliente.codigo_postal

        if not zip_code:
            return None

        return int(str(zip_code).strip())

    def _validate_request(self, request: BrokerQuoteRequest) -> None:
        missing = []

        if not request.cliente:
            missing.append("cliente")

        if not request.vehiculo:
            missing.append("vehiculo")

        if not request.vigencia_desde:
            missing.append("vigencia_desde")

        if not request.vigencia_hasta:
            missing.append("vigencia_hasta")

        if not request.cliente.nombre:
            missing.append("cliente.nombre")

        if not request.vehiculo.anio:
            missing.append("vehiculo.anio")

        if not (request.vehiculo.codigo_postal or request.cliente.codigo_postal):
            missing.append("codigo_postal")

        if missing:
            raise ValueError(
                "BrokerQuoteRequest incompleto para Chubb: "
                + ", ".join(missing)
            )

    def _validate_config(self, provider_config) -> None:
        required_fields = [
            "product_id",
            "businessprofile_id",
            "agent_id",
            "conduit_id",
            "grouping_id",
            "rate_id",
            "calculation_type_id",
            "payment_type_id",
            "vehicle_key",
            "vehicle_id",
            "insured_amount_type_id",
            "country_subdivision_id",
            "municipality_id",
            "use_id",
            "package_id",
        ]

        missing = [
            field
            for field in required_fields
            if not getattr(provider_config, field, None)
        ]

        if missing:
            raise ValueError(
                "Configuración Chubb incompleta para cotizar: "
                + ", ".join(missing)
            )
