from __future__ import annotations
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from cotizador.models import Cotizacion
from integrations.catalog import CatalogService
from integrations.quotes.contracts import (
    InternalQuoteRequest,
    QuoteDriver,
    QuotePackageRequest,
    QuoteRisk,
    QuoteVehicle,
)

class QuoteRequestService:
    """
    Construye el contrato canónico de cotización
    a partir de una Cotizacion del ERP.

    No conoce implementaciones específicas de aseguradoras.
    """

    VEHICLE_CATALOG_CODE = "VEHICLE"
    VEHICLE_USE_CATALOG_CODE = "VEHICLE_USE"
    STATE_CATALOG_CODE = "STATE"
    MUNICIPALITY_CATALOG_CODE = "MUNICIPALITY"
    PACKAGE_CATALOG_CODE = "COVERAGE_PACKAGE"

    @classmethod
    def build(
        cls,
        *,
        cotizacion: Cotizacion,
        provider_id: int,
        package_code: str,
        garage: bool,
        catalog_service=CatalogService,
    ) -> InternalQuoteRequest:

        cls._validate(
            cotizacion=cotizacion,
            provider_id=provider_id,
            package_code=package_code,
            garage=garage,
        )

        vehiculo = cotizacion.vehiculo

        vehicle_mapping = catalog_service.to_provider(
            provider_id=provider_id,
            catalog_code=cls.VEHICLE_CATALOG_CODE,
            internal_code=cls._vehicle_internal_code(
                vehiculo.catalogo_id
            ),
        )

        use_mapping = catalog_service.to_provider(
            provider_id=provider_id,
            catalog_code=cls.VEHICLE_USE_CATALOG_CODE,
            internal_code=vehiculo.tipo_uso,
        )

        state_mapping = catalog_service.to_provider(
            provider_id=provider_id,
            catalog_code=cls.STATE_CATALOG_CODE,
            internal_code=cotizacion.estado,
        )

        municipality_mapping = catalog_service.to_provider(
            provider_id=provider_id,
            catalog_code=cls.MUNICIPALITY_CATALOG_CODE,
            internal_code=cotizacion.ciudad,
        )

        package_mapping = catalog_service.to_provider(
            provider_id=provider_id,
            catalog_code=cls.PACKAGE_CATALOG_CODE,
            internal_code=package_code,
        )

        vehicle = QuoteVehicle(
            year=vehiculo.modelo_anio,
            vehicle_key=vehicle_mapping.external_code,
            use_code=use_mapping.external_code,
            garage=garage,
            state_code=state_mapping.external_code,
            municipality_code=municipality_mapping.external_code,
            plate=vehiculo.placas or None,
        )

        driver = QuoteDriver(
            age=cotizacion.conductor_edad,
            gender=cotizacion.conductor_genero,
        )

        package = QuotePackageRequest(
            code=package_mapping.external_code,
            selected=True,
            coverages=(),
        )

        risk = QuoteRisk(
            reference=cotizacion.folio,
            vehicle=vehicle,
            driver=driver,
            packages=(package,),
            discounts=(),
        )

        return InternalQuoteRequest(
            effective_date=cotizacion.vigencia_desde,
            expiration_date=cotizacion.vigencia_hasta,
            prospect_name=cotizacion.cliente.nombre_mostrar,
            reference=cotizacion.folio,
            risks=(risk,),
        )

    @staticmethod
    def _vehicle_internal_code(
        vehiculo_catalogo_id: int,
    ) -> str:
        return (
            f"VEHICULO_CATALOGO_{vehiculo_catalogo_id}"
        )

    @staticmethod
    def _validate(
        *,
        cotizacion: Cotizacion,
        provider_id: int,
        package_code: str,
        garage: bool,
    ) -> None:

        if not isinstance(cotizacion, Cotizacion):
            raise TypeError(
                "cotizacion debe ser una instancia de Cotizacion."
            )

        if not isinstance(provider_id, int) or provider_id <= 0:
            raise ValueError(
                "provider_id debe ser un entero mayor que cero."
            )

        if not isinstance(package_code, str) or not package_code.strip():
            raise ValueError(
                "package_code no puede estar vacío."
            )

        if not isinstance(garage, bool):
            raise TypeError(
                "garage debe ser booleano."
            )

        if cotizacion.tipo_cotizacion != Cotizacion.Tipo.INDIVIDUAL:
            raise ValueError(
                "Esta versión de QuoteRequestService sólo "
                "soporta cotizaciones individuales."
            )

        if cotizacion.vehiculo is None:
            raise ValueError(
                "La cotización no tiene vehículo."
            )

        if cotizacion.vehiculo.catalogo_id is None:
            raise ValueError(
                "El vehículo debe estar relacionado con "
                "VehiculoCatalogo para cotizar con proveedores."
            )

        if cotizacion.conductor_edad is None:
            raise ValueError(
                "La cotización no contiene edad del conductor."
            )

        if not cotizacion.conductor_genero:
            raise ValueError(
                "La cotización no contiene género del conductor."
            )

        if not cotizacion.estado.strip():
            raise ValueError(
                "La cotización no contiene estado."
            )

        if not cotizacion.ciudad.strip():
            raise ValueError(
                "La cotización no contiene ciudad/municipio."
            )

        if not cotizacion.cliente.nombre_mostrar.strip():
            raise ValueError(
                "El cliente no tiene un nombre disponible "
                "para la cotización."
            )

    @classmethod
    def to_dict(
        cls,
        request: InternalQuoteRequest,
    ) -> dict:
        if not isinstance(request, InternalQuoteRequest):
            raise TypeError(
                "request debe ser una instancia de "
                "InternalQuoteRequest."
            )

        return cls._json_safe(
            asdict(request)
        )

    @classmethod
    def _json_safe(cls, value):
        if isinstance(value, dict):
            return {
                key: cls._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                cls._json_safe(item)
                for item in value
            ]

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, Decimal):
            return str(value)

        return value
