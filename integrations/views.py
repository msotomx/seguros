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


import json

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from integrations.models import IntegrationEvent
from integrations.providers import get_provider
from integrations.providers.base import ProviderBusinessIgnore


def _pick_headers(request) -> dict:
    """
    Guardamos subset útil (evita almacenar TODO por privacidad/ruido).
    Django expone headers como request.headers (case-insensitive).
    """

    keys = [
        "x-signature",
        "x-request-id",
        "user-agent",
        "content-type",
        "x-forwarded-for",
        "x-forwarded-proto",
        "host",
        "referer",
        "traceparent",
    ]
    out = {}
    for k in keys:
        v = request.headers.get(k)
        if v:
            out[k] = v
    return out


@csrf_exempt
def webhook_in(request, provider: str):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    prov = get_provider(provider)
    if not prov:
        return HttpResponseBadRequest("Unknown provider")

    raw_body_bytes = request.body or b""
    raw_body_text = raw_body_bytes.decode("utf-8", errors="replace") if raw_body_bytes else ""

    # 1) Validar firma
    if not prov.validate_signature(request, raw_body_bytes):
        return JsonResponse({"ok": False, "error": "invalid_signature"}, status=401)

    # 2) payload
    #    Parse JSON (si no es JSON, payload=None pero raw_body sí se guarda)
    payload = None
    if raw_body_text.strip():
        try:
            payload = json.loads(raw_body_text)
        except Exception:
            payload = None

    # 3) Normalizar (debe sacar event_id aunque payload sea None, usando query params)
    try:
        normalized = prov.normalize_event(payload, request=request)
    except ProviderBusinessIgnore as e:
        # Evento válido pero no procesable (ej. falta data.id)
        # Respondemos 200 para que no reintente
        return JsonResponse({"ok": True, "ignored": True, "reason": str(e)})

    event_id = str(normalized.get("event_id") or "").strip()
    event_type = normalized.get("event_type", "") or ""
    dedupe_key = normalized.get("dedupe_key")
    object_type = normalized.get("object_type", "") or ""
    object_id = normalized.get("object_id", "") or ""

    if not event_id:
        return JsonResponse({"ok": False, "error": "missing_event_id"}, status=400)

    # headers relevantes
    headers_subset = _pick_headers(request)
    signature = request.headers.get("x-signature", "") or ""

    # 4) IntegrationEvent
    # Idempotencia (provider + event_id)
    # Guardamos SIEMPRE el evento recibido, sin procesar todavía
    try:
        with transaction.atomic():
            ie, created = IntegrationEvent.objects.get_or_create(
                provider=provider,
                event_id=event_id,
                defaults={
                    "event_type": event_type,
                    "signature": signature,
                    "headers": headers_subset or None,
                    "payload": payload,
                    "raw_body": raw_body_text[:200000],
                    "status": IntegrationEvent.Status.RECEIVED,
                    "received_at": timezone.now(),
                    "dedupe_key": dedupe_key,
                    "object_type": object_type,
                    "object_id": object_id,
                },
            )
    except Exception:
        created = False
        ie = IntegrationEvent.objects.filter(provider=provider, event_id=event_id).order_by("-id").first()

    if not created:
        # Ya existe; responder 200 para que el provider deje de reintentar        
        return JsonResponse({"ok": True, "deduped": True})

    # attempts, Incrementar attempts ANTES de procesar
    IntegrationEvent.objects.filter(id=ie.id).update(
        attempts=F("attempts") + 1,
        last_attempt_at=timezone.now(),
    )

    # 5) Procesar
    try:
        with transaction.atomic():
            prov.process(normalized)

            ie.status = IntegrationEvent.Status.PROCESSED
            ie.processed_at = timezone.now()
            ie.error_message = ""
            ie.save(update_fields=["status", "processed_at", "error_message"])

    except ProviderBusinessIgnore as e:
        ie.status = IntegrationEvent.Status.IGNORED
        ie.error_message = str(e)[:4000]
        ie.processed_at = timezone.now()
        ie.save(update_fields=["status", "error_message", "processed_at"])
        return JsonResponse({"ok": True, "ignored": True})

    except Exception as e:
        ie.status = IntegrationEvent.Status.ERROR
        ie.error_message = str(e)[:4000]
        ie.processed_at = timezone.now()
        ie.save(update_fields=["status", "error_message", "processed_at"])
        return JsonResponse({"ok": False, "error": "processing_failed"}, status=500)

    return JsonResponse({"ok": True})
