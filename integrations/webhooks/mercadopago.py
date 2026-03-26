import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from finanzas.services.reconciliation import conciliar_pago_mercadopago
from integrations.providers.mercadopago import MercadoPagoPaymentProvider

logger = logging.getLogger(__name__)


def _get_request_payload(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _extraer_payment_id(request, payload: dict):
    q = request.GET

    topic = (q.get("topic") or q.get("type") or "").strip().lower()
    if topic == "payment":
        return q.get("data.id") or q.get("id")

    action = str(payload.get("action") or "")
    if payload.get("type") == "payment":
        return payload.get("data", {}).get("id")

    if payload.get("topic") == "payment":
        return payload.get("data", {}).get("id")

    if action.startswith("payment."):
        return payload.get("data", {}).get("id")

    if payload.get("id") and payload.get("live_mode") is not None:
        return payload.get("id")

    return payload.get("data", {}).get("id")


@csrf_exempt
def mercadopago_webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    payload = _get_request_payload(request)

    topic = (request.GET.get("topic") or request.GET.get("type") or "").strip().lower()

    if topic == "merchant_order":
        print("IGNORADO merchant_order", flush=True)
        return JsonResponse({"ok": True, "ignored": "merchant_order"}, status=200)

    payment_id = _extraer_payment_id(request, payload)

    if not payment_id:
        return JsonResponse({"ok": False, "error": "No se encontró payment_id."}, status=200)

    provider = MercadoPagoPaymentProvider()

    try:
        payment_data = provider.obtener_pago(payment_id)
    except Exception as exc:
        logger.exception("Error consultando pago en MercadoPago")
        return JsonResponse({"ok": False, "error": str(exc)}, status=200)

    if not payment_data:
        return JsonResponse({"ok": False, "error": "MercadoPago devolvió respuesta vacía."}, status=200)

    try:
        pago = conciliar_pago_mercadopago(payment_data)
        return JsonResponse({"ok": True, "pago_id": pago.id}, status=200)
    except Exception as exc:
        logger.exception("Error conciliando pago")
        return JsonResponse({"ok": False, "error": str(exc)}, status=200)
    
