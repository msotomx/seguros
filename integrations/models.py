# integrations/models.py
from django.db import models
from django.utils import timezone

class IntegrationEvent(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Recibido"     # llegó y se guardó
        PROCESSED = "PROCESSED", "Procesado"  # se aplicó al sistema
        IGNORED = "IGNORED", "Ignorado"        # duplicado o no aplica
        ERROR = "ERROR", "Error"              # falló al procesar

    provider = models.CharField(max_length=40, db_index=True)  # "stripe", "conekta", "mock", "mercadopago"
    event_id = models.CharField(max_length=120, db_index=True) # id único del proveedor (evt_...)
    event_type = models.CharField(max_length=80, blank=True, default="", db_index=True)  # payment.succeeded, etc.

    # Request metadata (útil para debug / seguridad)
    signature = models.CharField(max_length=255, blank=True, default="")  # header firma (si aplica)
    headers = models.JSONField(null=True, blank=True)  # opcional (solo headers relevantes)
    payload = models.JSONField(null=True, blank=True)  # payload ya parseado JSON
    raw_body = models.TextField(blank=True, default="")  # por si no fue JSON o quieres el original

    # Estado de procesamiento
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.RECEIVED,
        db_index=True,
    )
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    error_message = models.TextField(blank=True, default="")
    error_trace = models.TextField(blank=True, default="")  # opcional (solo si quieres stacktrace)

    # Dedupe adicional / relación interna opcional
    dedupe_key = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text="Clave interna opcional (ej: PAGO_PAGADO:123). Complementa event_id."
    )
    object_type = models.CharField(max_length=40, blank=True, default="", db_index=True)  # "Pago", "Poliza"
    object_id = models.CharField(max_length=40, blank=True, default="", db_index=True)    # "123"

    # Operational fields
    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-received_at", "-id"]
        constraints = [
            # Idempotencia por proveedor + event_id
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="uq_integration_event_provider_event_id",
            ),
            # Idempotencia opcional por dedupe_key (solo cuando venga)
            models.UniqueConstraint(
                fields=["provider", "dedupe_key"],
                condition=models.Q(dedupe_key__isnull=False),
                name="uq_integration_event_provider_dedupe_key",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "status", "received_at"]),
            models.Index(fields=["provider", "event_type", "received_at"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.event_type}:{self.event_id} ({self.status})"

# Configuracion de la API    
class AseguradoraConfiguracion(models.Model):
    class Provider(models.TextChoices):
        CHUBB = "CHUBB", "Chubb"
        AXA = "AXA", "Axa"
        QUALITAS = "QUALITAS", "Qualitas"
        GNP = "GNP", "Gnp"
        GENERAL = "GENERAL", "General"

    class Ambiente(models.TextChoices):
        SIT = "SIT", "SIT"
        UAT = "UAT", "UAT"
        PROD = "PROD", "Producción"

    provider = models.CharField(max_length=30, choices=Provider.choices)
    ambiente = models.CharField(max_length=20, choices=Ambiente.choices, default=Ambiente.SIT)

    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)

    token_url = models.URLField()
    base_url = models.URLField()

    client_id = models.CharField(max_length=200)
    client_secret = models.TextField()
    resource_id = models.CharField(max_length=200)
    api_version = models.CharField(max_length=10, default="1")

    timeout = models.PositiveIntegerField(default=30)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "ambiente", "resource_id")
        verbose_name = "Configuración de aseguradora"
        verbose_name_plural = "Configuraciones de aseguradoras"

    def __str__(self):
        return f"{self.nombre} - {self.provider} {self.ambiente}"
