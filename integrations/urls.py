# integrations/urls.py
from django.urls import path
from .views import webhook_in

app_name = "integrations"

urlpatterns = [
    path("webhooks/<slug:provider>/", webhook_in, name="webhook_in"),
]
