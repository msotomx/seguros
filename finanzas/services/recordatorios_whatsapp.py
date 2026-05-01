from django.conf import settings

from integrations.providers.whatsapp import WhatsAppCloudProvider
from finanzas.services.recordatorios import registrar_recordatorio_pago


def normalizar_telefono_mx(numero: str) -> str:
    if not numero:
        return ""

    limpio = "".join(ch for ch in numero if ch.isdigit())

    if limpio.startswith("52"):
        return limpio

    if len(limpio) == 10:
        return "52" + limpio

    return limpio


def telefono_cliente_para_recordatorio(pago):
    cliente = pago.cliente
    if not cliente:
        return ""

    return normalizar_telefono_mx(
        cliente.telefono_principal or cliente.contacto_telefono or ""
    )


def enviar_recordatorio_whatsapp(*, pago, actor=None, categoria=None, dias=None):
    telefono = telefono_cliente_para_recordatorio(pago)
    if not telefono:
        return {"ok": False, "error": "Cliente sin teléfono válido"}

    provider = WhatsAppCloudProvider()

    cliente_nombre = pago.cliente.nombre_mostrar if pago.cliente else "Cliente"
    poliza_numero = pago.poliza.numero_poliza if pago.poliza else "-"
    monto = f"{pago.moneda} {pago.monto}"
    fecha_vencimiento = pago.fecha_vencimiento.strftime("%d/%m/%Y") if pago.fecha_vencimiento else "-"

    result = provider.send_template_recordatorio(
        to=telefono,
        cliente_nombre=cliente_nombre,
        poliza_numero=poliza_numero,
        monto=monto,
        fecha_vencimiento=fecha_vencimiento,
    )

    if result.get("ok"):
        registrar_recordatorio_pago(
            pago=pago,
            actor=actor,
            canal="WHATSAPP",
            categoria=categoria,
            dias=dias,
            usar_dedupe=True if categoria and dias is not None else False,
        )

    return result
