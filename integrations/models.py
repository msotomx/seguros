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

# Configuracion usada para Quote Engine

from django.db import models

from catalogos.models import Aseguradora


class AseguradoraConfiguracion(models.Model):
    class Provider(models.TextChoices):
        CHUBB = "CHUBB", "Chubb"
        AXA = "AXA", "AXA"
        QUALITAS = "QUALITAS", "Quálitas"
        GNP = "GNP", "GNP"
        GENERAL = "GENERAL", "General"

    class Ambiente(models.TextChoices):
        SIT = "SIT", "SIT"
        UAT = "UAT", "UAT"
        PROD = "PROD", "Producción"

    class Ramo(models.TextChoices):
        AUTOS = "AUTOS", "Autos"
        FLOTILLAS = "FLOTILLAS", "Flotillas"
        MOTOS = "MOTOS", "Motos"
        HOGAR = "HOGAR", "Hogar"
        VIDA = "VIDA", "Vida"
        OTRO = "OTRO", "Otro"

    aseguradora = models.ForeignKey(
        Aseguradora,
        on_delete=models.PROTECT,
        related_name="configuraciones_api",
        null=True,
        blank=True,
    )

    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
        db_index=True,
    )

    ambiente = models.CharField(
        max_length=20,
        choices=Ambiente.choices,
        default=Ambiente.SIT,
        db_index=True,
    )

    ramo = models.CharField(
        max_length=30,
        choices=Ramo.choices,
        default=Ramo.AUTOS,
        db_index=True,
    )

    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True, db_index=True)
    prioridad = models.PositiveIntegerField(default=100, db_index=True)

    token_url = models.URLField(blank=True, default="")
    base_url = models.URLField()

    client_id = models.CharField(max_length=200, blank=True, default="")
    client_secret = models.TextField(blank=True, default="")
    resource_id = models.CharField(max_length=200, blank=True, default="")
    api_version = models.CharField(max_length=10, default="1")
    timeout = models.PositiveIntegerField(default=30)
    grouping_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    rate_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Identificador de tarifa asignado por la aseguradora.",
    )
    business_profile_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    business_profile_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    source_application_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    supports_quote = models.BooleanField(default=False)
    supports_issue = models.BooleanField(default=False)
    supports_documents = models.BooleanField(default=False)
    supports_payments = models.BooleanField(default=False)
    supports_endorsements = models.BooleanField(default=False)
    supports_cancellation = models.BooleanField(default=False)
    supports_renewal = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "ambiente", "ramo", "resource_id"],
                name="uq_provider_config_env_ramo_resource",
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "ambiente", "activo"],
                name="idx_provider_env_active",
            ),
            models.Index(
                fields=["ramo", "activo", "prioridad"],
                name="idx_provider_ramo_priority",
            ),
        ]
        ordering = ["prioridad", "provider"]
        verbose_name = "Configuración de aseguradora"
        verbose_name_plural = "Configuraciones de aseguradoras"

    def __str__(self):
        return (
            f"{self.nombre} - {self.provider} "
            f"{self.ambiente} / {self.ramo}"
        )
    
class ProviderSetting(models.Model):
    class ValueType(models.TextChoices):
        STRING = "STRING", "Texto"
        INTEGER = "INTEGER", "Entero"
        DECIMAL = "DECIMAL", "Decimal"
        BOOLEAN = "BOOLEAN", "Booleano"
        JSON = "JSON", "JSON"

    configuracion = models.ForeignKey(
        AseguradoraConfiguracion,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    key = models.CharField(max_length=100)
    value = models.TextField(blank=True, default="")

    value_type = models.CharField(
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.STRING,
    )

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    activo = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuracion", "key"],
                name="uq_provider_setting_config_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["configuracion", "activo"],
                name="idx_provider_setting_active",
            ),
        ]
        ordering = ["key"]
        verbose_name = "Parámetro del Provider"
        verbose_name_plural = "Parámetros de Providers"

    def __str__(self):
        return f"{self.configuracion.provider}: {self.key}"

from django.db import models

# Catalogo Canonico
# Representa un tipo de catálogo reconocido por Switchh.

class Catalog(models.Model):
    code = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
    )
    name = models.CharField(
        max_length=150,
    )
    description = models.TextField(
        blank=True,
        default="",
    )
    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Catálogo"
        verbose_name_plural = "Catálogos"

    def __str__(self):
        return f"{self.code} - {self.name}"

"""
# CatalogItem: Elementos canonicos
# Cada catálogo contiene valores internos normalizados.

Metadata permitirá extender elementos sin modificar continuamente el esquema:
{
  "country": "MX",
  "sat_code": "CHH",
  "aliases": ["Chihuahua", "Chih."]
}
    No debe utilizarse para guardar configuraciones críticas del provider.
"""

class CatalogItem(models.Model):
    catalog = models.ForeignKey(
        Catalog,
        on_delete=models.CASCADE,
        related_name="items",
    )
    code = models.CharField(
        max_length=120,
    )
    name = models.CharField(
        max_length=200,
    )
    description = models.TextField(
        blank=True,
        default="",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Elemento de catálogo"
        verbose_name_plural = "Elementos de catálogo"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "code"],
                name="uq_catalog_item_catalog_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["catalog", "is_active"],
                name="idx_catalog_item_active",
            ),
        ]

    def __str__(self):
        return f"{self.catalog.code}:{self.code}"

from django.core.exceptions import ValidationError
from django.db import models


class ProviderCatalogMapping(models.Model):
    provider = models.ForeignKey(
        "integrations.AseguradoraConfiguracion",
        on_delete=models.CASCADE,
        related_name="catalog_mappings",
        verbose_name="Configuración de aseguradora",
    )

    catalog = models.ForeignKey(
        Catalog,
        on_delete=models.CASCADE,
        related_name="provider_mappings",
        verbose_name="Catálogo",
    )

    catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.CASCADE,
        related_name="provider_mappings",
        verbose_name="Elemento de catálogo",
    )

    external_code = models.CharField(
        max_length=200,
        verbose_name="Código externo",
    )

    external_name = models.CharField(
        max_length=250,
        blank=True,
        default="",
        verbose_name="Nombre externo",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        ordering = [
            "provider",
            "catalog",
            "catalog_item__sort_order",
            "catalog_item__name",
        ]
        verbose_name = "Mapeo de catálogo por provider"
        verbose_name_plural = "Mapeos de catálogo por provider"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "provider",
                    "catalog_item",
                ],
                name="uq_provider_catalog_item",
            ),
            models.UniqueConstraint(
                fields=[
                    "provider",
                    "catalog",
                    "external_code",
                ],
                name="uq_provider_catalog_external_code",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "provider",
                    "catalog",
                    "is_active",
                ],
                name="idx_provider_catalog_active",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.catalog_id
            and self.catalog_item_id
            and self.catalog_item.catalog_id != self.catalog_id
        ):
            raise ValidationError(
                {
                    "catalog_item": (
                        "El elemento seleccionado no pertenece "
                        "al catálogo indicado."
                    ),
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.provider} | "
            f"{self.catalog.code}:"
            f"{self.catalog_item.code} → "
            f"{self.external_code}"
        )
