import requests
from django.conf import settings


class WhatsAppCloudProvider:
    def __init__(self):
        self.enabled = bool(getattr(settings, "WHATSAPP_ENABLED", False))
        self.access_token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        self.template_name = getattr(settings, "WHATSAPP_TEMPLATE_RECORDATORIO", "recordatorio_pago")
        self.api_version = getattr(settings, "WHATSAPP_API_VERSION", "v23.0")

    @property
    def base_url(self):
        return f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_template_recordatorio(self, *, to, cliente_nombre, poliza_numero, monto, fecha_vencimiento):
        if not self.enabled:
            return {"ok": False, "error": "WhatsApp disabled in settings"}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": self.template_name,
                "language": {"code": "es_MX"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": cliente_nombre},
                            {"type": "text", "text": poliza_numero},
                            {"type": "text", "text": monto},
                            {"type": "text", "text": fecha_vencimiento},
                        ],
                    }
                ],
            },
        }

        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=30)

        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": resp.text}

        return {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "data": data,
        }
