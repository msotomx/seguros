# integrations/views.py
import json
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, transaction
from django.utils import timezone

from integrations.models import IntegrationEvent
from integrations.providers import get_provider
from integrations.providers.mercadopago import ProviderBusinessIgnore
import hashlib

def fallback_event_id(self, raw_body_bytes: bytes, payload: dict, request=None) -> str:
    h = hashlib.sha256(raw_body_bytes).hexdigest()
    return f"bodysha256:{h}"


def _extract_headers(request) -> dict:
    """
    Guarda solo headers útiles. Evita meter todo (por ruido/PII).
    """
    keep = [
        "HTTP_USER_AGENT",
        "HTTP_X_REQUEST_ID",
        "HTTP_X_SIGNATURE",
        "HTTP_STRIPE_SIGNATURE",
        "HTTP_X_WEBHOOK_SIGNATURE",
        "CONTENT_TYPE",
    ]
    return {k: request.META.get(k) for k in keep if request.META.get(k) is not None}

from django.db.models import F

import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def webhook_in(request, provider: str):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    prov = get_provider(provider)
    if not prov:
        return HttpResponseBadRequest("Unknown provider")

    raw_body = request.body or b""

    # 1) Validación de firma
    # (para MercadoPago a veces depende de headers + query params)
    if not prov.validate_signature(request, raw_body):
        return JsonResponse({"ok": False, "error": "invalid_signature"}, status=401)

    # 2) Parse JSON si se puede; si no, continuar (NO 400)
    payload = None
    if raw_body.strip():
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            payload = None  # <- clave: no fallar

    # 3) Normaliza evento (debe soportar payload None)
    normalized = prov.normalize_event(payload, request=request)
    event_id = str(normalized["event_id"])
    event_type = normalized.get("event_type", "")
    dedupe_key = normalized.get("dedupe_key")  # opcional
    obj_type = normalized.get("object_type", "")
    obj_id = normalized.get("object_id", "")

    # 4) Idempotencia: registrar IntegrationEvent
    try:
        with transaction.atomic():
            ie, created = IntegrationEvent.objects.get_or_create(
                provider=provider,
                event_id=event_id,  # OJO: tu modelo se llama event_id
                defaults={
                    "event_type": event_type,
                    "payload": payload,
                    "raw_body": raw_body.decode("utf-8", errors="ignore"),
                    "headers": {
                        "x-signature": request.headers.get("x-signature", ""),
                        "x-request-id": request.headers.get("x-request-id", ""),
                        "content-type": request.headers.get("content-type", ""),
                    },
                    "signature": request.headers.get("x-signature", ""),
                    "status": IntegrationEvent.Status.RECEIVED,
                    "dedupe_key": dedupe_key,
                    "object_type": obj_type,
                    "object_id": str(obj_id),
                },
            )
    except Exception:
        # carrera por unique constraint
        created = False
        ie = IntegrationEvent.objects.filter(provider=provider, event_id=event_id).first()

    # incrementa attempts SIEMPRE (creado o deduped)
    IntegrationEvent.objects.filter(provider=provider, event_id=event_id).update(
        attempts=F("attempts") + 1,
        last_attempt_at=timezone.now(),
    )

    if not created:
        return JsonResponse({"ok": True, "deduped": True})

    # 5) Procesar
    try:
        with transaction.atomic():
            prov.process(normalized)
            ie.status = IntegrationEvent.Status.PROCESSED
            ie.processed_at = timezone.now()
            ie.save(update_fields=["status", "processed_at"])

    except ProviderBusinessIgnore as e:
        ie.status = IntegrationEvent.Status.IGNORED
        ie.error_message = str(e)[:4000]
        ie.processed_at = timezone.now()
        ie.save(update_fields=["status", "error_message", "processed_at"])
        return JsonResponse({"ok": True, "ignored": True})

    except Exception as e:
        msg = str(e)

        # Si el provider da un error tipo "Payment not found" o status=404 -> IGNORED
        if "status=404" in msg or "Payment not found" in msg:
            ie.status = IntegrationEvent.Status.IGNORED
            ie.error_message = msg[:4000]
            ie.processed_at = timezone.now()
            ie.save(update_fields=["status", "error_message", "processed_at"])
            return JsonResponse({"ok": True, "ignored": True})

        ie.status = IntegrationEvent.Status.ERROR
        ie.error_message = msg[:4000]
        ie.processed_at = timezone.now()
        ie.save(update_fields=["status", "error_message", "processed_at"])
        return JsonResponse({"ok": False, "error": "processing_failed"}, status=500)