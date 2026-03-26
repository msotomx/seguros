# integrations/urls.py
from django.urls import path
from integrations.webhooks.mercadopago import mercadopago_webhook
# from integrations.views import webhook_in

app_name = "integrations"

urlpatterns = [
    path("webhooks/mercadopago/", mercadopago_webhook, name="mercadopago_webhook"),
    # path("webhooks/<slug:provider>/", webhook_in, name="webhook_in"),
]
