from __future__ import annotations
import os
import re

import hmac
import hashlib
import requests
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from integrations.providers.base import BaseProvider
from finanzas.models import Pago
from polizas.models import PolizaEvento
from polizas.services import log_poliza_event

from integrations.providers.base import ProviderBusinessIgnore

    
class MercadoPagoProvider:
    """
    Provider MercadoPago (webhooks).
    Flujo:
      1) webhook llega con query param data.id=<payment_id>
      2) GET /v1/payments/{payment_id}
      3) extrae external_reference="PAGO:<pago_id>"
      4) actualiza Pago + crea PolizaEvento con dedupe_key
    """

    API_BASE = "https://api.mercadopago.com"

    def __init__(self, *, access_token=None, webhook_secret=None):
        self.access_token = access_token or os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
        self.webhook_secret = webhook_secret or os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")

    def _parse_x_signature(self, x_signature: str):
        """
        x-signature ejemplo:
        ts=1704908010,v1=618c85345248dd820d5fd456117c2ab2ef8eda45a0282ff693eac24131a5e839
        """
        ts = None
        v1 = None

        if not x_signature:
            return ts, v1

        parts = [p.strip() for p in x_signature.split(",") if p.strip()]
        for p in parts:
            if p.startswith("ts="):
                ts = p.split("=", 1)[1].strip()
            elif p.startswith("v1="):
                v1 = p.split("=", 1)[1].strip()

        return ts, v1

    def _get_query_param(self, request, key: str) -> str:
        # request.GET también sirve, pero así queda consistente
        full_path = request.get_full_path()
        query = urlparse(full_path).query
        params = parse_qs(query)
        return (params.get(key, [""])[0] or "").strip()

    def validate_signature(self, request, raw_body: bytes) -> bool:
        """
        Validación de firma MercadoPago.
        Si MP_VALIDATE_SIGNATURE=False, no valida (modo DEV).
        """

        # 🔧 DEV: permitir saltar validación
        if not settings.MP_VALIDATE_SIGNATURE:
            return True

        secret = self.webhook_secret
        if not secret:
            return False

        x_signature = request.headers.get("x-signature", "") or ""
        x_request_id = request.headers.get("x-request-id", "") or ""
        data_id = self._get_query_param(request, "data.id")

        ts, v1 = self._parse_x_signature(x_signature)

        if not (ts and v1 and x_request_id and data_id):
            return False

        # Mercado Pago recomienda lower() si data.id es alfanumérico
        data_id = data_id.lower()

        signed_template = f"id:{data_id};request-id:{x_request_id};ts:{ts};"

        generated = hmac.new(
            key=secret.encode("utf-8"),
            msg=signed_template.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated, v1)    

    # ---------------------------------------------------------------------
    # Normalización: sacar payment_id desde query params o payload
    # ---------------------------------------------------------------------
    def normalize_event(self, payload, request=None):
        payload = payload or {}

        payment_id = ""
        if request is not None:
            payment_id = request.GET.get("data.id", "") or request.GET.get("id", "")

        if not payment_id:
            payment_id = (payload.get("data") or {}).get("id") or payload.get("id")

        if not payment_id:
            raise ProviderBusinessIgnore("mercadopago: missing data.id", code="MISSING_DATA_ID")

        payment_id = str(payment_id).strip()

        return {
            "event_id": payment_id,
            "event_type": (payload.get("type") or "payment"),
            "action": (payload.get("action") or ""),
            "data": {"payment_id": payment_id},
            "dedupe_key": f"MP_PAYMENT:{payment_id}",
            "object_type": "Pago",
            "object_id": "",  # se llenará cuando resolvamos external_reference
        }

    # ---------------------------------------------------------------------
    # PROCESO PRINCIPAL
    # ---------------------------------------------------------------------
    @transaction.atomic
    def process(self, normalized: dict):
        payment_id = (normalized.get("data") or {}).get("payment_id")
        if not payment_id:
            raise ProviderBusinessIgnore("mercadopago: missing payment_id", code="MISSING_PAYMENT_ID")

        mp_payment = self._fetch_payment(payment_id)

        # 1) Obtener external_reference y mapear a Pago interno
        external_reference = (mp_payment.get("external_reference") or "").strip()
        if not external_reference:
            raise ProviderBusinessIgnore(
                f"mercadopago: payment {payment_id} without external_reference",
                code="MISSING_EXTERNAL_REFERENCE",
            )

        pago_id = self._parse_pago_id(external_reference)
        if not pago_id:
            raise ProviderBusinessIgnore(
                f"mercadopago: invalid external_reference '{external_reference}' payment={payment_id}",
                code="INVALID_EXTERNAL_REFERENCE",
            )

        try:
            pago = Pago.objects.select_related("poliza").get(id=pago_id)
        except Pago.DoesNotExist:
            raise ProviderBusinessIgnore(
                f"mercadopago: Pago not found id={pago_id} payment={payment_id}",
                code="PAGO_NOT_FOUND",
            )

        # 2) Interpretar status MP
        status = (mp_payment.get("status") or "").lower().strip()
        status_detail = (mp_payment.get("status_detail") or "").lower().strip()

        # Mapeo simplificado (puedes ajustar después)
        # approved => pagado
        if status == "approved":
            self._apply_pago_pagado(pago, mp_payment, payment_id, status_detail)
            return

        # rejected => NO cambiar a VENCIDO/CANCELADO, se queda PENDIENTE (regla tuya)
        if status in {"rejected", "cancelled", "charged_back", "refunded"}:
            self._apply_pago_rechazado(pago, mp_payment, payment_id, status, status_detail)
            return

        # pending / in_process / authorized / etc: no hacemos nada
        raise ProviderBusinessIgnore(
            f"mercadopago: ignoring status={status} detail={status_detail} payment={payment_id}",
            code="STATUS_IGNORED",
        )

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _fetch_payment(self, payment_id: str) -> dict:
        if not self.access_token:
            raise RuntimeError("mercadopago: MERCADOPAGO_ACCESS_TOKEN is missing")

        url = f"{self.API_BASE}/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        r = requests.get(url, headers=headers, timeout=25)

        if r.status_code == 404:
            raise ProviderBusinessIgnore(
                f"mercadopago: payment not found id={payment_id}",
                code="PAYMENT_NOT_FOUND",
            )

        if r.status_code >= 400:
            body = (r.text or "")[:2000]
            raise RuntimeError(f"mercadopago: GET payment failed status={r.status_code} body={body}")

        return r.json()

    def _parse_pago_id(self, external_reference: str) -> int | None:
        """
        Esperamos: "PAGO:<id>"
        """
        m = re.match(r"^PAGO:(\d+)$", external_reference.strip(), flags=re.IGNORECASE)
        if not m:
            return None
        return int(m.group(1))

    def _apply_pago_pagado(self, pago: Pago, mp_payment: dict, payment_id: str, status_detail: str):
        # idempotencia por estado: si ya está pagado, no duplicar
        if pago.estatus != Pago.Estatus.PAGADO:
            pago.estatus = Pago.Estatus.PAGADO
            pago.fecha_pago = timezone.localdate()
            pago.metodo = "MERCADOPAGO"
            pago.referencia = str(payment_id)
            pago.save(update_fields=["estatus", "fecha_pago", "metodo", "referencia", "updated_at"])

        # bitácora con dedupe_key + UniqueConstraint
        log_poliza_event(
            poliza=pago.poliza,
            tipo=PolizaEvento.Tipo.PAGO_PAGADO,
            actor=None,
            titulo="Pago confirmado por MercadoPago",
            detalle=f"Payment {payment_id} (approved) {status_detail}".strip(),
            dedupe_key=f"PAGO_PAGADO:{pago.id}",
            data={
                "pago_id": pago.id,
                "payment_id": str(payment_id),
                "status": mp_payment.get("status"),
                "status_detail": mp_payment.get("status_detail"),
                "transaction_amount": mp_payment.get("transaction_amount"),
                "payment_method_id": mp_payment.get("payment_method_id"),
            },
        )

    def _apply_pago_rechazado(self, pago: Pago, mp_payment: dict, payment_id: str, status: str, status_detail: str):
        # Regla: pago rechazado => dejar PENDIENTE (no tocar a VENCIDO/CANCELADO aquí)
        if pago.estatus != Pago.Estatus.PENDIENTE:
            pago.estatus = Pago.Estatus.PENDIENTE
            pago.save(update_fields=["estatus", "updated_at"])

        log_poliza_event(
            poliza=pago.poliza,
            tipo=PolizaEvento.Tipo.PAGO_RECHAZADO,
            actor=None,
            titulo="Pago rechazado por MercadoPago",
            detalle=f"Payment {payment_id} ({status}) {status_detail}".strip(),
            dedupe_key=f"PAGO_RECHAZADO:{pago.id}",
            data={
                "pago_id": pago.id,
                "payment_id": str(payment_id),
                "status": mp_payment.get("status"),
                "status_detail": mp_payment.get("status_detail"),
                "transaction_amount": mp_payment.get("transaction_amount"),
                "payment_method_id": mp_payment.get("payment_method_id"),
            },
        )

import mercadopago
from django.conf import settings


class MercadoPagoPaymentProvider:
    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    def obtener_pago(self, payment_id):
        response = self.sdk.payment().get(payment_id)
        return response.get("response", {}) if isinstance(response, dict) else {}