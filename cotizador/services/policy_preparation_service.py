from django.db import transaction

from cotizador.models import CotizacionItem
from polizas.models import Poliza, PolizaEvento
from polizas.services import log_poliza_event


class PolicyPreparationService:

    @classmethod
    @transaction.atomic
    def prepare(
        cls,
        *,
        cotizacion_item: CotizacionItem,
    ) -> Poliza:
        if not isinstance(cotizacion_item, CotizacionItem):
            raise ValueError("cotizacion_item inválido.")

        cotizacion = cotizacion_item.cotizacion

        existing = (
            Poliza.objects
            .select_for_update()
            .filter(cotizacion_item=cotizacion_item)
            .first()
        )

        if existing is not None:
            return existing        

        poliza = Poliza.objects.create(
            cliente=cotizacion.cliente,
            vehiculo=cotizacion.vehiculo,
            flotilla=cotizacion.flotilla,
            aseguradora=cotizacion_item.aseguradora,
            producto=cotizacion_item.producto,
            cotizacion_item=cotizacion_item,
            numero_poliza=f"PEND-COT-{cotizacion_item.id}",
            fecha_emision=None,
            vigencia_desde=cotizacion.vigencia_desde,
            vigencia_hasta=cotizacion.vigencia_hasta,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_neta=cotizacion_item.prima_neta,
            gastos_expedicion=cotizacion_item.derechos,
            iva=cotizacion_item.iva,
            prima_total=cotizacion_item.prima_total,
            forma_pago=cotizacion_item.forma_pago,
        )

        log_poliza_event(
            poliza=poliza,
            tipo=PolizaEvento.Tipo.CREADA,
            titulo="Póliza preparada para pago",
            detalle="Se creó la póliza en proceso previa a la confirmación del pago.",
            data={
                "cotizacion_id": cotizacion.id,
                "cotizacion_item_id": cotizacion_item.id,
                "estatus": Poliza.Estatus.EN_PROCESO,
            },
            dedupe_key=f"POLIZA_CREADA:{poliza.id}",
        )

        return poliza
