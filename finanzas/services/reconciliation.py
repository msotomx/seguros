from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finanzas.models import Pago, PagoTransaccion
from finanzas.services.application import aplicar_pago_a_objeto_negocio


ESTATUS_APROBADOS_MP = {"approved", "accredited"}
ESTATUS_PENDIENTES_MP = {"pending", "in_process", "authorized"}
ESTATUS_RECHAZADOS_MP = {"rejected", "cancelled", "refunded", "charged_back"}


def _to_decimal(value, default=None):
    if value in (None, "", False):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _normalizar_metodo_mp(raw_method):
    if not raw_method:
        return None

    raw = str(raw_method).lower().strip()

    mapping = {
        "credit_card": Pago.Metodo.TARJETA,
        "debit_card": Pago.Metodo.TARJETA,
        "account_money": Pago.Metodo.MERCADOPAGO,
        "bank_transfer": Pago.Metodo.TRANSFERENCIA,
        "ticket": Pago.Metodo.OXXO,
    }
    return mapping.get(raw, Pago.Metodo.OTRO)


def _build_summary(data: dict) -> dict:
    return {
        "provider": Pago.Provider.MERCADOPAGO,
        "provider_payment_id": data.get("provider_payment_id"),
        "provider_preference_id": data.get("provider_preference_id"),
        "provider_status": data.get("provider_status"),
        "monto": str(data.get("monto")) if data.get("monto") is not None else "",
        "moneda": data.get("moneda"),
        "metodo_raw": data.get("metodo_raw"),
        "referencia": data.get("referencia"),
        "pago_id": data.get("internal_pago_id"),
        "poliza_id": data.get("poliza_id"),
    }


def extraer_datos_mp(payload: dict) -> dict:
    metadata = payload.get("metadata") or {}
    payer = payload.get("payer") or {}
    transaction_details = payload.get("transaction_details") or {}

    internal_pago_id = (
        metadata.get("pago_id")
        or payload.get("external_reference")
        or payload.get("pago_id")
    )

    internal_pago_id = int(internal_pago_id) if str(internal_pago_id).isdigit() else None

    return {
        "provider": Pago.Provider.MERCADOPAGO,
        "provider_payment_id": str(payload.get("id") or ""),
        "provider_preference_id": (
            payload.get("order", {}).get("id")
            or payload.get("preference_id")
            or metadata.get("provider_preference_id")
            or ""
        ),
        "provider_status": str(payload.get("status") or "").lower().strip(),
        "monto": _to_decimal(
            payload.get("transaction_amount"),
            default=_to_decimal(transaction_details.get("total_paid_amount"))
        ),
        "moneda": payload.get("currency_id") or "MXN",
        "metodo_raw": payload.get("payment_type_id") or payload.get("payment_method_id"),
        "referencia": (
            payload.get("authorization_code")
            or transaction_details.get("external_resource_url")
            or str(payload.get("id") or "")
        ),
        "internal_pago_id": internal_pago_id,
        "poliza_id": metadata.get("poliza_id"),
        "payer_email": payer.get("email"),
        "fecha_pago_provider": payload.get("date_approved") or payload.get("date_created"),
        "raw": payload,
    }


def localizar_pago_desde_payload(data: dict):
    internal_pago_id = data.get("internal_pago_id")
    provider_payment_id = data.get("provider_payment_id")
    provider_preference_id = data.get("provider_preference_id")

    qs = Pago.objects.select_related("poliza", "cliente")

    if internal_pago_id:
        pago = qs.filter(pk=internal_pago_id).first()
        if pago:
            return pago

    if provider_payment_id:
        pago = qs.filter(provider_payment_id=provider_payment_id).first()
        if pago:
            return pago

    if provider_preference_id:
        pago = qs.filter(provider_preference_id=provider_preference_id).first()
        if pago:
            return pago

    return None


def _resolver_estatus_local(pago: Pago, monto_conciliado, provider_status: str) -> str:
    if provider_status in ESTATUS_APROBADOS_MP:
        if monto_conciliado is None:
            return Pago.Estatus.PENDIENTE_REVISION
        if monto_conciliado == pago.monto:
            return Pago.Estatus.PAGADO
        if monto_conciliado < pago.monto:
            return Pago.Estatus.PARCIAL
        return Pago.Estatus.PENDIENTE_REVISION

    if provider_status in ESTATUS_PENDIENTES_MP:
        return Pago.Estatus.EN_PROCESO

    if provider_status in ESTATUS_RECHAZADOS_MP:
        return Pago.Estatus.RECHAZADO

    return Pago.Estatus.PENDIENTE_REVISION


def _tipo_transaccion_por_status(provider_status: str) -> str:
    if provider_status in ESTATUS_APROBADOS_MP:
        return PagoTransaccion.Tipo.PAYMENT_APPROVED
    if provider_status in ESTATUS_PENDIENTES_MP:
        return PagoTransaccion.Tipo.PAYMENT_PENDING
    if provider_status in ESTATUS_RECHAZADOS_MP:
        return PagoTransaccion.Tipo.PAYMENT_REJECTED
    return PagoTransaccion.Tipo.RECONCILIACION_OK


def _parse_fecha_provider(value):
    if not value:
        return None
    try:
        dt = timezone.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


@transaction.atomic
def conciliar_pago_mercadopago(payload: dict) -> Pago:
    data = extraer_datos_mp(payload)
    pago = localizar_pago_desde_payload(data)

    if not pago:
        raise ValidationError("No fue posible localizar el pago para este webhook.")

    pago = (
        Pago.objects.select_for_update()
        .select_related("poliza", "cliente")
        .get(pk=pago.pk)
    )

    provider_status = data.get("provider_status") or ""
    provider_payment_id = data.get("provider_payment_id") or ""
    metodo = _normalizar_metodo_mp(data.get("metodo_raw"))
    referencia = data.get("referencia") or provider_payment_id
    fecha_pago_provider = _parse_fecha_provider(data.get("fecha_pago_provider"))

    monto_conciliado = data.get("monto")
    if monto_conciliado is None:
        monto_conciliado = pago.monto_pagado

    PagoTransaccion.objects.create(
        pago=pago,
        provider=Pago.Provider.MERCADOPAGO,
        tipo=PagoTransaccion.Tipo.WEBHOOK_RECIBIDO,
        provider_payment_id=provider_payment_id or None,
        provider_preference_id=data.get("provider_preference_id") or None,
        provider_status=provider_status or None,
        monto=monto_conciliado,
        moneda=data.get("moneda") or pago.moneda,
        payload=payload,
        observaciones="Webhook recibido desde MercadoPago.",
        procesado=True,
    )

    if (
        pago.estatus == Pago.Estatus.PAGADO
        and pago.provider_payment_id
        and provider_payment_id
        and pago.provider_payment_id == provider_payment_id
        and provider_status in ESTATUS_APROBADOS_MP
    ):
        return pago

    nuevo_estatus = _resolver_estatus_local(
        pago=pago,
        monto_conciliado=monto_conciliado,
        provider_status=provider_status,
    )

    pago.provider = Pago.Provider.MERCADOPAGO
    pago.provider_payment_id = provider_payment_id or pago.provider_payment_id

    update_fields = [
        "provider",
        "provider_payment_id",
        "updated_at",
    ]

    if data.get("provider_preference_id"):
        pago.provider_preference_id = data["provider_preference_id"]
        update_fields.append("provider_preference_id")

    if provider_status:
        pago.provider_status = provider_status
        update_fields.append("provider_status")

    if monto_conciliado is not None:
        pago.monto_pagado = monto_conciliado
        update_fields.append("monto_pagado")

    if data.get("moneda"):
        pago.moneda = data["moneda"]
        update_fields.append("moneda")

    if metodo:
        pago.metodo = metodo
        update_fields.append("metodo")

    if referencia:
        pago.referencia = referencia
        update_fields.append("referencia")

    if fecha_pago_provider:
        pago.fecha_pago_provider = fecha_pago_provider
        update_fields.append("fecha_pago_provider")

    pago.webhook_last_payload = payload
    pago.payload_resumen_json = _build_summary(data)
    pago.estatus = nuevo_estatus

    update_fields.extend([
        "webhook_last_payload",
        "payload_resumen_json",
        "estatus",
    ])

    if nuevo_estatus == Pago.Estatus.PAGADO:
        pago.fecha_pago = timezone.localdate()
        update_fields.append("fecha_pago")

    pago.save(update_fields=list(dict.fromkeys(update_fields)))

    PagoTransaccion.objects.create(
        pago=pago,
        provider=Pago.Provider.MERCADOPAGO,
        tipo=_tipo_transaccion_por_status(provider_status),
        provider_payment_id=provider_payment_id or None,
        provider_preference_id=data.get("provider_preference_id") or None,
        provider_status=provider_status or None,
        monto=monto_conciliado,
        moneda=data.get("moneda") or pago.moneda,
        payload=payload,
        observaciones=f"Conciliación aplicada. Estatus local: {nuevo_estatus}.",
        procesado=True,
    )

    if pago.estatus == Pago.Estatus.PAGADO:
        try:
            aplicar_pago_a_objeto_negocio(pago)
        except Exception as exc:
            # No revertimos el pago por fallas en efectos secundarios
            PagoTransaccion.objects.create(
                pago=pago,
                provider=Pago.Provider.MERCADOPAGO,
                tipo=PagoTransaccion.Tipo.RECONCILIACION_ERROR,
                provider_payment_id=provider_payment_id or None,
                provider_preference_id=data.get("provider_preference_id") or None,
                provider_status=provider_status or None,
                monto=monto_conciliado,
                moneda=data.get("moneda") or pago.moneda,
                payload=payload,
                observaciones=f"Pago conciliado, pero falló aplicar_pago_a_objeto_negocio: {exc}",
                procesado=False,
                error_message=str(exc),
            )

    return pago
