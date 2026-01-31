from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint, CheckConstraint
from core.models import TimeStampedModel, MoneyMixin
from crm.models import Cliente
from autos.models import Vehiculo, Flotilla
from catalogos.models import Aseguradora, ProductoSeguro, CoberturaCatalogo
from tarifas.models import ReglaTarifa

from django.db import transaction
from django.utils import timezone

# ---------------------------------------------------------------------
# Folios de Cotizaciones 
# ---------------------------------------------------------------------
class FolioCotizacionCounter(models.Model):
    anio = models.PositiveIntegerField(unique=True)
    last = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.anio} -> {self.last}"

    @classmethod
    def next_folio(cls, anio: int) -> str:
        with transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(anio=anio)
            counter.last += 1
            counter.save()
            return f"COT-{anio}-{counter.last:06d}"

# ---------------------------------------------------------------------
# Cotizaciones / Comparativos (A + B)
# ---------------------------------------------------------------------

class Cotizacion(TimeStampedModel):
    class Origen(models.TextChoices):
        PORTAL_PUBLICO = "PORTAL_PUBLICO", "Portal público"
        CRM = "CRM", "CRM interno"
        AGENTE = "AGENTE", "Agente"
        API = "API", "API"

    origen = models.CharField(
        max_length=20,
        choices=Origen.choices,
        default=Origen.CRM,
        db_index=True,
    )

    class Tipo(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        FLOTILLA = "FLOTILLA", "Flotilla"

    class Estatus(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ENVIADA = "ENVIADA", "Enviada"
        ACEPTADA = "ACEPTADA", "Aceptada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        VENCIDA = "VENCIDA", "Vencida"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="cotizaciones")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="cotizaciones")
    flotilla = models.ForeignKey(Flotilla, on_delete=models.SET_NULL, null=True, blank=True, related_name="cotizaciones")
    
    tipo_cotizacion = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    folio = models.CharField(max_length=20, unique=True, db_index=True, blank=True, default="") 
    
    vigencia_desde = models.DateField(db_index=True)
    vigencia_hasta = models.DateField(db_index=True)

    forma_pago_preferida = models.CharField(max_length=30, blank=True, default="", db_index=True)
    notas = models.TextField(blank=True, default="")
    estatus = models.CharField(max_length=10, choices=Estatus.choices, default=Estatus.BORRADOR, db_index=True)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cotizaciones")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cotizaciones_creadas",
    )

    class Meta:
        constraints = [
            # Individual: vehiculo != null AND flotilla == null
            # Flotilla: flotilla != null AND vehiculo == null
            CheckConstraint(
                name="ck_cotizacion_individual_o_flotilla",
                check=(
                    (Q(tipo_cotizacion="INDIVIDUAL") & Q(vehiculo__isnull=False) & Q(flotilla__isnull=True)) |
                    (Q(tipo_cotizacion="FLOTILLA") & Q(flotilla__isnull=False) & Q(vehiculo__isnull=True))
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["cliente", "estatus", "created_at"]),
            models.Index(fields=["owner", "estatus"]),
        ]
        permissions = [
            ("send_cotizacion", "Puede enviar cotización"),
            ("approve_cotizacion", "Puede marcar cotización como aceptada"),
        ]

    def save(self, *args, **kwargs):
        if not self.folio:
            anio = (self.vigencia_desde.year if self.vigencia_desde else timezone.localdate().year)
            self.folio = FolioCotizacionCounter.next_folio(anio)
        super().save(*args, **kwargs)

class CotizacionItem(TimeStampedModel, MoneyMixin):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="items")
    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.PROTECT, related_name="cotizacion_items")
    producto = models.ForeignKey(ProductoSeguro, on_delete=models.PROTECT, related_name="cotizacion_items")

    # resultados (para A y/o B)
    prima_neta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    derechos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    recargos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuentos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    prima_total = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_index=True)

    forma_pago = models.CharField(max_length=30, blank=True, default="")
    meses = models.PositiveIntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default="")
    ranking = models.IntegerField(default=0, db_index=True)
    seleccionada = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["cotizacion", "aseguradora", "producto"], name="uq_cotizacion_item_unico"),
        ]
        indexes = [
            models.Index(fields=["cotizacion", "ranking"]),
            models.Index(fields=["aseguradora", "producto"]),
        ]


class CotizacionItemCobertura(TimeStampedModel):
    item = models.ForeignKey(CotizacionItem, on_delete=models.CASCADE, related_name="coberturas")
    cobertura = models.ForeignKey(CoberturaCatalogo, on_delete=models.PROTECT)
    incluida = models.BooleanField(default=True)
    valor = models.CharField(max_length=120, blank=True, default="")
    notas = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["item", "cobertura"], name="uq_item_cobertura"),
        ]


class CotizacionItemCalculo(TimeStampedModel):
    """
    Resultado del motor (B). Guarda trazabilidad del cálculo.
    """
    item = models.OneToOneField(CotizacionItem, on_delete=models.CASCADE, related_name="calculo")
    prima_base = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    factor_total = models.DecimalField(max_digits=14, decimal_places=6, default=1)
    detalle_json = models.JSONField(default=dict, blank=True)

    class Meta:
        permissions = [
            ("view_calculo_cotizacion", "Puede ver detalle de cálculo de cotización"),
        ]


class CotizacionItemReglaAplicada(TimeStampedModel):
    class Resultado(models.TextChoices):
        APLICO = "APLICO", "Aplicó"
        NO_APLICO = "NO_APLICO", "No aplicó"
        RECHAZO = "RECHAZO", "Rechazó"

    item = models.ForeignKey(CotizacionItem, on_delete=models.CASCADE, related_name="reglas_aplicadas")
    regla = models.ForeignKey(ReglaTarifa, on_delete=models.PROTECT)
    resultado = models.CharField(max_length=10, choices=Resultado.choices, db_index=True)
    valor_resultante = models.CharField(max_length=200, blank=True, default="")
    mensaje = models.TextField(blank=True, default="")
    orden = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["item", "orden"])]


# Flotilla (desglose opcional)
class CotizacionFlotillaItemVehiculo(TimeStampedModel, MoneyMixin):
    item = models.ForeignKey(CotizacionItem, on_delete=models.CASCADE, related_name="flotilla_vehiculos")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="cotizaciones_flotilla")
    prima_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    detalle_json = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["item", "vehiculo"], name="uq_item_vehiculo_flotilla")]
