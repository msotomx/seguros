import os
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from finanzas.models import Pago


class Command(BaseCommand):
    help = "Crea una preferencia de MercadoPago (Checkout Pro) para pruebas sandbox (webhook)."

    def add_arguments(self, parser):
        parser.add_argument("--pago-id", type=int, required=True)
        parser.add_argument("--webhook-url", type=str, required=True)
        parser.add_argument("--title", type=str, default="Pago Seguro Auto (Sandbox)")
        parser.add_argument("--amount", type=float, default=None)

    def handle(self, *args, **opts):
        pago_id = opts["pago_id"]
        webhook_url = opts["webhook_url"].rstrip("/") + "/"
        title = opts["title"]
        amount = opts["amount"]

        token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "") or os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
        if not token:
            raise CommandError("Falta MERCADOPAGO_ACCESS_TOKEN en settings")

        pago = Pago.objects.get(id=pago_id)
        unit_price = float(amount if amount is not None else pago.monto)

        url = "https://api.mercadopago.com/checkout/preferences"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "items": [{
                "title": title,
                "quantity": 1,
                "unit_price": float(unit_price),  # 790.0
                "currency_id": "MXN",
            }],
            "external_reference": f"PAGO:{pago.id}",
            "notification_url": webhook_url,
        }

        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code >= 400:
            raise CommandError(f"MP error {r.status_code}: {r.text[:600]}")

        data = r.json()
        self.stdout.write(self.style.SUCCESS("Preferencia creada ✅"))
        self.stdout.write(f"external_reference: PAGO:{pago.id}")
        self.stdout.write(f"notification_url: {webhook_url}")
        self.stdout.write(f"id: {data.get('id')}")
        self.stdout.write(f"sandbox_init_point: {data.get('sandbox_init_point')}")
        self.stdout.write(f"init_point: {data.get('init_point')}")
