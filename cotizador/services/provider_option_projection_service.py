from __future__ import annotations

from django.db import transaction

from catalogos.models import (
    Aseguradora,
    ProductoSeguro,
)
from cotizador.models import (
    CotizacionItem,
    CotizacionProveedor,
)
from integrations.broker.provider_configuration import (
    ProviderConfiguration,
)


class ProviderOptionProjectionService:
    """
    Proyecta opciones técnicas de un proveedor a CotizacionItem.

    CotizacionProveedorOpcion representa el resultado técnico.
    CotizacionItem representa la opción comercial mostrable en UI.

    No conoce implementaciones específicas de aseguradoras.
    """

    @classmethod
    @transaction.atomic
    def project(
        cls,
        *,
        resultado_proveedor: CotizacionProveedor,
        configuration: ProviderConfiguration,
    ) -> tuple[CotizacionItem, ...]:

        if not isinstance(
            resultado_proveedor,
            CotizacionProveedor,
        ):
            raise TypeError(
                "resultado_proveedor debe ser una instancia "
                "de CotizacionProveedor."
            )

        if not isinstance(
            configuration,
            ProviderConfiguration,
        ):
            raise TypeError(
                "configuration debe ser una instancia "
                "de ProviderConfiguration."
            )

        if not resultado_proveedor.success:
            raise ValueError(
                "Sólo pueden proyectarse resultados "
                "exitosos del proveedor."
            )

        provider_code = (
            resultado_proveedor.provider_code
            .strip()
            .upper()
        )

        configuration_provider = (
            configuration.provider
            .strip()
            .upper()
        )

        if provider_code != configuration_provider:
            raise ValueError(
                "La configuración no corresponde al "
                "provider del resultado."
            )

        if configuration.aseguradora_id is None:
            raise ValueError(
                "La configuración no contiene aseguradora_id."
            )

        if configuration.producto_seguro_id is None:
            raise ValueError(
                "La configuración no contiene "
                "producto_seguro_id."
            )

        try:
            aseguradora = Aseguradora.objects.get(
                pk=configuration.aseguradora_id,
                is_active=True,
            )
        except Aseguradora.DoesNotExist as exc:
            raise ValueError(
                "La aseguradora configurada no existe "
                "o está inactiva."
            ) from exc

        try:
            producto = ProductoSeguro.objects.get(
                pk=configuration.producto_seguro_id,
                aseguradora=aseguradora,
                is_active=True,
            )
        except ProductoSeguro.DoesNotExist as exc:
            raise ValueError(
                "El producto configurado no existe, "
                "está inactivo o no corresponde "
                "a la aseguradora."
            ) from exc

        opciones = (
            resultado_proveedor.opciones
            .select_related(
                "riesgo",
            )
            .order_by(
                "id",
            )
        )

        created_items: list[CotizacionItem] = []

        for ranking, opcion in enumerate(
            opciones,
            start=1,
        ):
            item, _created = (
                CotizacionItem.objects.update_or_create(
                    provider_option=opcion,
                    defaults={
                        "cotizacion": (
                            resultado_proveedor.cotizacion
                        ),
                        "aseguradora": aseguradora,
                        "producto": producto,

                        # No inventamos desglose económico
                        # que el paquete no proporciona.
                        "prima_neta": 0,
                        "derechos": 0,
                        "recargos": 0,
                        "descuentos": 0,
                        "iva": 0,

                        "prima_total": (
                            opcion.total_premium
                        ),

                        "ranking": ranking,
                        "seleccionada": False,

                        "provider": provider_code,
                        "provider_quote_id": (
                            resultado_proveedor
                            .provider_quote_id
                        ),
                        "provider_raw_response": (
                            resultado_proveedor
                            .response_json
                            or {}
                        ),

                        "paquete_nombre": (
                            opcion.name
                            or (
                                "Paquete "
                                f"{opcion.provider_package_id}"
                            )
                        ),
                    },
                )
            )

            created_items.append(item)

        return tuple(created_items)
