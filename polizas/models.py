from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint, CheckConstraint
from django.utils import timezone
from core.models import TimeStampedModel, SoftDeleteModel, MoneyMixin
from documentos.models import Documento
from crm.models import Cliente
from autos.models import Vehiculo, Conductor, Flotilla
from catalogos.models import Aseguradora, ProductoSeguro
from cotizador.models import CotizacionItem
from core.models import FormaPagoChoices

# ---------------------------------------------------------------------
# Pólizas / Endosos / Renovaciones
# ---------------------------------------------------------------------
class Poliza(TimeStampedModel, MoneyMixin):
    class Estatus(models.TextChoices):
        EN_PROCESO = "EN_PROCESO", "En proceso"
        VIGENTE = "VIGENTE", "Vigente"
        VENCIDA = "VENCIDA", "Vencida"
        CANCELADA = "CANCELADA", "Cancelada"

    class MotivoCancelacion(models.TextChoices):
            FALTA_PAGO = "FALTA_PAGO", "Falta de pago"
            SOLICITUD_CLIENTE = "SOLICITUD_CLIENTE", "Solicitud del cliente"
            ERROR_EMISION = "ERROR_EMISION", "Error en emisión"
            CAMBIO_ASEGURADORA = "CAMBIO_ASEGURADORA", "Cambio de aseguradora"
            OTRO = "OTRO", "Otro"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="polizas")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")
    flotilla = models.ForeignKey(Flotilla, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")

    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.PROTECT, related_name="polizas")
    producto = models.ForeignKey(ProductoSeguro, on_delete=models.PROTECT, related_name="polizas")
    cotizacion_item = models.ForeignKey(CotizacionItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")

    numero_poliza = models.CharField(max_length=80, db_index=True)
    fecha_emision = models.DateField(null=True,blank=True,db_index=True,
                                     help_text="Fecha en que la póliza fue emitida")
    vigencia_desde = models.DateField(db_index=True)
    vigencia_hasta = models.DateField(db_index=True)
    estatus = models.CharField(max_length=12, choices=Estatus.choices, default=Estatus.EN_PROCESO, db_index=True)

    prima_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    forma_pago = models.CharField(
        max_length=30,
        choices=FormaPagoChoices.choices,
        default=FormaPagoChoices.CONTADO,
        blank=True,
        db_index=True,
    )
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")
    documento = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")
    fecha_cancelacion = models.DateField(null=True, blank=True, db_index=True)
    motivo_cancelacion = models.CharField(max_length=30, choices=MotivoCancelacion.choices, 
                                          blank=True, default="",)
    motivo_cancelacion_detalle = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["aseguradora", "numero_poliza"], name="uq_poliza_por_aseguradora"),
            CheckConstraint(
                name="ck_poliza_individual_o_flotilla",
                check=(Q(vehiculo__isnull=False, flotilla__isnull=True) | Q(flotilla__isnull=False, vehiculo__isnull=True)),
            ),
        ]
        indexes = [
            models.Index(fields=["cliente", "estatus"]),
            models.Index(fields=["vigencia_hasta", "estatus"]),
            models.Index(fields=["fecha_emision", "estatus"]),
        ]
        permissions = [
            ("manage_polizas", "Puede administrar pólizas"),
            ("renew_poliza", "Puede renovar póliza"),
        ]

    def __str__(self):
        return f"{self.numero_poliza} ({self.aseguradora.nombre})"


class Endoso(TimeStampedModel):
    class Tipo(models.TextChoices):
        CAMBIO_DATOS = "CAMBIO_DATOS", "Cambio de datos"
        CAMBIO_VEHICULO = "CAMBIO_VEHICULO", "Cambio de vehículo"
        AUMENTO_COBERTURA = "AUMENTO_COBERTURA", "Aumento cobertura"
        OTRO = "OTRO", "Otro"

    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, related_name="endosos")
    tipo_endoso = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    fecha = models.DateField(default=timezone.now, db_index=True)
    descripcion = models.TextField(blank=True, default="")
    prima_ajuste = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    documento = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="endosos")


class Renovacion(TimeStampedModel):
    poliza_anterior = models.ForeignKey(Poliza, on_delete=models.PROTECT, related_name="renovaciones_salientes")
    poliza_nueva = models.ForeignKey(Poliza, on_delete=models.PROTECT, related_name="renovaciones_entrantes")
    fecha_renovacion = models.DateField(default=timezone.now, db_index=True)
    resultado = models.CharField(max_length=30, blank=True, default="", db_index=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["poliza_anterior", "poliza_nueva"], name="uq_renovacion_unica")]

# ---------------------------------------------------------------------
# Incidentes / Siniestros (riesgo)
# ---------------------------------------------------------------------

class Incidente(TimeStampedModel):
    class Tipo(models.TextChoices):
        CHOQUE = "CHOQUE", "Choque"
        ROBO = "ROBO", "Robo"
        DANIOS = "DANIOS", "Daños"
        RC = "RC", "Responsabilidad civil"
        INFRACCION = "INFRACCION", "Infracción"
        OTRO = "OTRO", "Otro"

    class Estatus(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        CERRADO = "CERRADO", "Cerrado"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="incidentes")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidentes")
    conductor = models.ForeignKey(Conductor, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidentes")
    tipo_incidente = models.CharField(max_length=15, choices=Tipo.choices, db_index=True)
    fecha_incidente = models.DateField(db_index=True)
    descripcion = models.TextField(blank=True, default="")
    monto_estimado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    resolucion = models.TextField(blank=True, default="")
    estatus = models.CharField(max_length=10, choices=Estatus.choices, default=Estatus.ABIERTO, db_index=True)
    documento = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidentes")

    class Meta:
        indexes = [models.Index(fields=["cliente", "fecha_incidente"])]

        permissions = [
            ("manage_incidentes", "Puede administrar incidentes"),
        ]


class Siniestro(TimeStampedModel):
    class Estatus(models.TextChoices):
        REPORTADO = "REPORTADO", "Reportado"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        PAGADO = "PAGADO", "Pagado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        CERRADO = "CERRADO", "Cerrado"

    incidente = models.ForeignKey(Incidente, on_delete=models.SET_NULL, null=True, blank=True, related_name="siniestros")
    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.PROTECT, related_name="siniestros")
    numero_siniestro = models.CharField(max_length=60, blank=True, default="", db_index=True)
    fecha_reporte = models.DateField(db_index=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    estatus = models.CharField(max_length=12, choices=Estatus.choices, default=Estatus.REPORTADO, db_index=True)
    monto_reclamado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    monto_pagado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notas = models.TextField(blank=True, default="")
    documento = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="siniestros")

    class Meta:
        indexes = [
            models.Index(fields=["aseguradora", "estatus"]),
            models.Index(fields=["fecha_reporte"]),
        ]

class PolizaEvento(models.Model):

    class Tipo(models.TextChoices):
        CREADA = "CREADA", "Creada"
        NUMERO_ACTUALIZADO = "NUMERO_ACTUALIZADO", "Número actualizado"
        VIGENCIA_ACTUALIZADA = "VIGENCIA_ACTUALIZADA", "Vigencia actualizada"
        MARCADA_VIGENTE = "MARCADA_VIGENTE", "Marcada como vigente"
        CANCELADA = "CANCELADA", "Cancelada"
        RENOVADA = "RENOVADA", "Renovada"
        PAGO_VENCIDO = "PAGO_VENCIDO", "Pago vencido"
        PAGO_PAGADO = "PAGO_PAGADO", "Pago pagado"
        PAGO_CANCELADO = "PAGO_CANCELADO", "Pago cancelado"
        PAGO_RECHAZADO = "PAGO_RECHAZADO", "Pago rechazado"
        PAGO_COMPROBANTE_ADJUNTADO = "PAGO_COMPROBANTE_ADJUNTADO", "Comprobante de pago adjuntado"
        POLIZA_DOCUMENTO_ADJUNTADO = "POLIZA_DOCUMENTO_ADJUNTADO", "Documento de póliza adjuntado"
        POLIZA_VENCIDA = "POLIZA_VENCIDA", "Póliza Vencida"
        

    poliza = models.ForeignKey("polizas.Poliza", on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=40, choices=Tipo.choices, db_index=True)
    titulo = models.CharField(max_length=120, blank=True, default="")
    detalle = models.TextField(blank=True, default="")
    data = models.JSONField(blank=True, null=True)  # opcional (antes/después, etc.)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    dedupe_key = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text="Clave para evitar duplicados. Ej: PAGO_VENCIDO:123"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["poliza", "tipo", "dedupe_key"],
                condition=Q(dedupe_key__isnull=False),
                name="uq_poliza_event_dedupe_key",
            ),
        ]

    def __str__(self):
        return f"{self.poliza_id} {self.tipo} {self.created_at:%Y-%m-%d %H:%M}"

