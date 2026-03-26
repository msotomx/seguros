from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse

from finanzas.models import Pago, PagoTransaccion


def _nombre_cliente_para_pago(cliente) -> str:
    if not cliente:
        return "Cliente"
    if hasattr(cliente, "nombre_mostrar") and cliente.nombre_mostrar:
        return cliente.nombre_mostrar
    return str(cliente)


def _concepto_pago(pago: Pago) -> str:
    if pago.concepto:
        return pago.concepto

    if pago.poliza_id and getattr(pago.poliza, "numero_poliza", None):
        return f"Pago de póliza {pago.poliza.numero_poliza}"

    return f"Pago #{pago.id}"


def _build_return_urls(request) -> dict:
    return {
        "success": request.build_absolute_uri(
            reverse("portal:pago_return", kwargs={"status": "success"})
        ),
        "pending": request.build_absolute_uri(
            reverse("portal:pago_return", kwargs={"status": "pending"})
        ),
        "failure": request.build_absolute_uri(
            reverse("portal:pago_return", kwargs={"status": "failure"})
        ),
    }


def _build_notification_url(request) -> str:
    return request.build_absolute_uri(reverse("integrations:mercadopago_webhook"))


def _crear_preferencia_mercadopago(*, pago: Pago, back_urls: dict, notification_url: str) -> dict:
    """
    Encapsula la llamada al provider.
    Aquí puedes usar el SDK oficial o tu wrapper actual.
    Debe regresar un dict normalizado.
    """
    import mercadopago

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    external_reference = str(pago.id)
    title = _concepto_pago(pago)
    cliente_nombre = _nombre_cliente_para_pago(pago.cliente)

    preference_data = {
        "items": [
            {
                "title": title,
                "description": pago.descripcion or title,
                "quantity": 1,
                "currency_id": pago.moneda or "MXN",
                "unit_price": float(pago.monto),
            }
        ],
        "payer": {
            "name": cliente_nombre,
            "email": getattr(pago.cliente, "email_principal", "") or "",
        },
        "external_reference": external_reference,
        "notification_url": notification_url,
        "back_urls": back_urls,
        "auto_return": "approved",
        "metadata": {
            "pago_id": pago.id,
            "poliza_id": pago.poliza_id,
            "cliente_id": pago.cliente_id,
        },
    }

    response = sdk.preference().create(preference_data)
    data = response.get("response", {}) if isinstance(response, dict) else {}

    if not data or "id" not in data:
        raise ValidationError("No fue posible crear la preferencia en MercadoPago.")

    return {
        "provider": Pago.Provider.MERCADOPAGO,
        "provider_preference_id": data.get("id"),
        "checkout_url": data.get("init_point") or data.get("sandbox_init_point"),
        "provider_status": data.get("status") or "created",
        "raw": data,
    }


@transaction.atomic
def crear_checkout_pago(pago: Pago, request=None, actor=None) -> dict:
    """
    Crea un checkout/link de pago para un Pago.
    """
    if not pago.pk:
        raise ValidationError("El pago debe existir antes de generar checkout.")

    pago = Pago.objects.select_for_update().select_related("cliente", "poliza").get(pk=pago.pk)

    if not pago.puede_generar_checkout():
        raise ValidationError("Este pago no puede generar checkout en su estado actual.")

    if pago.estatus == Pago.Estatus.PAGADO:
        raise ValidationError("Este pago ya fue pagado.")

    if pago.monto is None or pago.monto <= Decimal("0.00"):
        raise ValidationError("El monto del pago debe ser mayor a cero.")

    if request is None:
        raise ValidationError("Se requiere request para construir URLs de retorno y webhook.")

    back_urls = _build_return_urls(request)
    notification_url = _build_notification_url(request)

    provider_result = _crear_preferencia_mercadopago(
        pago=pago,
        back_urls=back_urls,
        notification_url=notification_url,
    )

    pago.provider = provider_result["provider"]
    pago.provider_preference_id = provider_result["provider_preference_id"]
    pago.checkout_url = provider_result["checkout_url"]
    pago.provider_status = provider_result["provider_status"] or "created"
    pago.payload_resumen_json = {
        "provider": pago.provider,
        "provider_preference_id": pago.provider_preference_id,
        "checkout_url": pago.checkout_url,
        "provider_status": pago.provider_status,
    }

    if pago.estatus == Pago.Estatus.PENDIENTE:
        pago.estatus = Pago.Estatus.EN_PROCESO

    update_fields = [
        "provider",
        "provider_preference_id",
        "checkout_url",
        "provider_status",
        "payload_resumen_json",
        "estatus",
        "updated_at",
    ]
    pago.save(update_fields=update_fields)

    PagoTransaccion.objects.create(
        pago=pago,
        provider=pago.provider,
        tipo=PagoTransaccion.Tipo.CHECKOUT_CREADO,
        provider_preference_id=pago.provider_preference_id,
        provider_status=pago.provider_status,
        monto=pago.monto,
        moneda=pago.moneda,
        payload=provider_result["raw"],
        observaciones="Checkout creado correctamente.",
        procesado=True,
    )

    return {
        "ok": True,
        "pago_id": pago.id,
        "provider": pago.provider,
        "provider_preference_id": pago.provider_preference_id,
        "checkout_url": pago.checkout_url,
    }
