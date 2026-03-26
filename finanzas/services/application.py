# ¿para qué sirve application.py aquí?
#
# sirve para lógica post-pago, por ejemplo:
#
# registrar evento en bitácora de póliza
# actualizar métricas o saldos
# marcar mensualidad/cobro como cubierto
# adjuntar comprobante si aplica
# disparar notificación al cliente o agente

from polizas.models import PolizaEvento
from polizas.services import log_poliza_event

def aplicar_pago_a_objeto_negocio(pago, actor=None):
    if pago.estatus != pago.Estatus.PAGADO:
        return

    poliza = pago.poliza
    if not poliza:
        return

    dedupe_key = f"PAGO_PAGADO:{pago.id}"

    log_poliza_event(
        poliza=poliza,
        tipo=PolizaEvento.Tipo.PAGO_PAGADO,
        titulo = "Pago confirmado por MercadoPago" if pago.provider == "MERCADOPAGO" else "Pago confirmado manualmente",
        detalle = f"Se confirmó el pago #{pago.id} por {pago.moneda} {pago.monto_pagado or pago.monto}.",
        actor=actor,
        data={
            "pago_id": pago.id,
            "monto": str(pago.monto_pagado or pago.monto),
            "moneda": pago.moneda,
            "metodo": pago.metodo,
            "referencia": pago.referencia,
            "provider": pago.provider,
            "provider_payment_id": pago.provider_payment_id,
            "provider_status": pago.provider_status,
            "_dedupe_key": dedupe_key,
        },
        dedupe_key=dedupe_key,
    )

    return