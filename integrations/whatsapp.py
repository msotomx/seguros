import requests

from django.conf import settings


class WhatsAppError(Exception):
    pass


def enviar_mensaje_texto_whatsapp(*, telefono, mensaje):
    url = (
        f"https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": mensaje,
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)

    if response.status_code >= 400:
        raise WhatsAppError(response.text)

    return response.json()


def normalizar_telefono_mx(telefono):
    telefono = (telefono or "").strip()
    telefono = telefono.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")

    if not telefono:
        return ""

    if telefono.startswith("52"):
        return telefono

    return f"52{telefono}"


def construir_mensaje_recordatorio_pago(pago):
    cliente = pago.poliza.cliente if pago.poliza and pago.poliza.cliente else "cliente"
    poliza = getattr(pago.poliza, "numero_poliza", None) or pago.poliza_id
    monto = pago.monto
    fecha = pago.fecha_vencimiento or getattr(pago, "fecha_programada", None)

    fecha_txt = fecha.strftime("%d/%m/%Y") if fecha else "próxima"

    return (
        f"Hola {cliente}, te recordamos que tienes un pago pendiente "
        f"de la póliza {poliza} por ${monto}, con vencimiento {fecha_txt}. "
        f"Para cualquier duda, por favor comunícate con tu agente."
    )


def enviar_recordatorio_pago_whatsapp(*, pago, usuario=None):
    cliente = pago.poliza.cliente if pago.poliza else None

    telefono = getattr(cliente, "telefono_principal", "")
    telefono = normalizar_telefono_mx(telefono)

    if not telefono:
        raise WhatsAppError("El cliente no tiene teléfono/celular registrado.")

    mensaje = construir_mensaje_recordatorio_pago(pago)

    response_json = enviar_mensaje_texto_whatsapp_ok(
        telefono=telefono,
        mensaje=mensaje,
    )

    return response_json

# ==========================================================
# Envio de WA al nuevo cliente del Portal
# ==========================================================
def construir_mensaje_acceso_portal(cliente, user, password_temporal):
    return (
        f"Hola {cliente.nombre_mostrar}, tu póliza ha sido generada.\n\n"
        f"Ya puedes consultar tus pólizas, pagos y documentos en el portal.\n\n"
        f"Usuario: {user.username}\n"
        f"Contraseña temporal: {password_temporal}\n\n"
        f"Te recomendamos cambiar tu contraseña al ingresar.\n"
        f"{settings.HOME_PAGE}"
    )


def enviar_acceso_portal_whatsapp(*, cliente, user, password_temporal):
    telefono = normalizar_telefono_mx(cliente.telefono_principal)

    if not telefono:
        raise WhatsAppError("El cliente no tiene teléfono principal registrado.")

    mensaje = construir_mensaje_acceso_portal(
        cliente=cliente,
        user=user,
        password_temporal=password_temporal,
    )


    return enviar_mensaje_texto_whatsapp(
        telefono=telefono,
        mensaje=mensaje,
    )
