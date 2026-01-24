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

# ---------------------------------------------------------------------
# Pólizas / Endosos / Renovaciones
# ---------------------------------------------------------------------

class Poliza(TimeStampedModel, MoneyMixin):
    class Estatus(models.TextChoices):
        EN_PROCESO = "EN_PROCESO", "En proceso"
        VIGENTE = "VIGENTE", "Vigente"
        VENCIDA = "VENCIDA", "Vencida"
        CANCELADA = "CANCELADA", "Cancelada"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="polizas")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")
    flotilla = models.ForeignKey(Flotilla, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")

    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.PROTECT, related_name="polizas")
    producto = models.ForeignKey(ProductoSeguro, on_delete=models.PROTECT, related_name="polizas")
    cotizacion_item = models.ForeignKey(CotizacionItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")

    numero_poliza = models.CharField(max_length=80, db_index=True)
    vigencia_desde = models.DateField(db_index=True)
    vigencia_hasta = models.DateField(db_index=True)
    estatus = models.CharField(max_length=12, choices=Estatus.choices, default=Estatus.EN_PROCESO, db_index=True)

    prima_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    forma_pago = models.CharField(max_length=30, blank=True, default="")

    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")
    documento = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="polizas")

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
