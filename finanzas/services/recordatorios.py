from django.utils.timezone import localdate

from polizas.models import PolizaEvento
from polizas.services import log_poliza_event


def construir_mensaje_recordatorio(pago, *, categoria=None, dias=None):
    cliente = pago.cliente.nombre_mostrar if pago.cliente else "Cliente"
    poliza = pago.poliza.numero_poliza if pago.poliza else "-"
    fecha_vencimiento = pago.fecha_vencimiento.strftime("%d/%m/%Y") if pago.fecha_vencimiento else "-"
    monto = f"{pago.moneda} {pago.monto}"

    if categoria == "VENCIDO" or pago.estatus == pago.Estatus.VENCIDO:
        if dias is not None:
            return (
                f"Hola {cliente}, te recordamos que el pago de tu póliza {poliza} "
                f"por {monto} venció el {fecha_vencimiento} y presenta {dias} día(s) de atraso. "
                f"Te pedimos ponerte al corriente a la brevedad."
            )
        return (
            f"Hola {cliente}, te recordamos que el pago de tu póliza {poliza} "
            f"por {monto} venció el {fecha_vencimiento}. "
            f"Te pedimos ponerte al corriente a la brevedad."
        )

    if dias is not None:
        return (
            f"Hola {cliente}, te recordamos que el pago de tu póliza {poliza} "
            f"por {monto} vence el {fecha_vencimiento}, en {dias} día(s). "
            f"Te invitamos a realizar tu pago oportunamente."
        )

    return (
        f"Hola {cliente}, te recordamos que el pago de tu póliza {poliza} "
        f"por {monto} vence el {fecha_vencimiento}. "
        f"Te invitamos a realizar tu pago oportunamente."
    )


def registrar_recordatorio_pago(
    *,
    pago,
    actor=None,
    canal="MANUAL",
    categoria=None,
    dias=None,
    usar_dedupe=False,
):
    mensaje = construir_mensaje_recordatorio(pago, categoria=categoria, dias=dias)

    dedupe_key = None
    if usar_dedupe and categoria and dias is not None:
        dedupe_key = f"PAGO_RECORDATORIO_ENVIADO:{pago.id}:{categoria}:{dias}"

    if pago.poliza:
        log_poliza_event(
            poliza=pago.poliza,
            tipo=PolizaEvento.Tipo.PAGO_RECORDATORIO_ENVIADO,
            actor=actor,
            titulo="Recordatorio de pago enviado",
            detalle=f"Se generó recordatorio para el pago #{pago.id}.",
            data={
                "pago_id": pago.id,
                "canal": canal,
                "categoria": categoria or "",
                "dias": dias if dias is not None else "",
                "estatus_pago": pago.estatus,
                "fecha_programada": str(pago.fecha_programada) if pago.fecha_programada else "",
                "fecha_vencimiento": str(pago.fecha_vencimiento) if pago.fecha_vencimiento else "",
                "monto": str(pago.monto),
                "moneda": pago.moneda,
                "referencia": pago.referencia,
                "mensaje": mensaje,
                "fecha_envio": str(localdate()),
            },
            dedupe_key=dedupe_key,
        )

    return mensaje
