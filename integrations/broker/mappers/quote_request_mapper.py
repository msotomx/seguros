# integrations/broker/mappers/quote_mapper.py
# quote_request_mapper.py -> construye la solicitud que el Broker enviará a los Providers.

from integrations.broker.contracts import (
    BrokerQuoteRequest,
    BrokerCustomerData,
    BrokerVehicleData,
)


class BrokerQuoteRequestMapper:
    @staticmethod
    def from_cotizacion(cotizacion) -> BrokerQuoteRequest:
        cliente = getattr(cotizacion, "cliente", None)
        vehiculo = getattr(cotizacion, "vehiculo", None)

        customer_data = BrokerCustomerData(
            tipo_cliente=getattr(cliente, "tipo_cliente", "") if cliente else "",
            nombre=str(cliente) if cliente else "",
            email=getattr(cliente, "email", None) if cliente else None,
            telefono=getattr(cliente, "telefono", None) if cliente else None,
            codigo_postal=getattr(cliente, "codigo_postal", None) if cliente else None,
            ciudad=getattr(cliente, "ciudad", None) if cliente else None,
            estado=getattr(cliente, "estado", None) if cliente else None,
            nombre_comercial=getattr(cliente, "nombre_comercial", None) if cliente else None,
        )

        vehicle_data = BrokerVehicleData(
            tipo_uso=getattr(vehiculo, "uso", None) if vehiculo else None,
            anio=getattr(vehiculo, "anio", None) if vehiculo else None,
            marca=str(getattr(vehiculo, "marca", "")) if vehiculo else None,
            submarca=str(getattr(vehiculo, "submarca", "")) if vehiculo else None,
            version=getattr(vehiculo, "version", None) if vehiculo else None,
            placas=getattr(vehiculo, "placas", None) if vehiculo else None,
            vin=getattr(vehiculo, "vin", None) if vehiculo else None,
            codigo_postal=getattr(cliente, "codigo_postal", None) if cliente else None,
        )

        return BrokerQuoteRequest(
            cotizacion_id=getattr(cotizacion, "id", None),
            cliente=customer_data,
            vehiculo=vehicle_data,
            vigencia_desde=getattr(cotizacion, "vigencia_desde", None),
            vigencia_hasta=getattr(cotizacion, "vigencia_hasta", None),
            forma_pago=getattr(cotizacion, "forma_pago_preferida", None),
            notas=getattr(cotizacion, "notas", None),
            raw={
                "cotizacion_id": getattr(cotizacion, "id", None),
                "folio": getattr(cotizacion, "folio", None),
            },
        )
