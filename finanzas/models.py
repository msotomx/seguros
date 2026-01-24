from django.conf import settings
from django.db import models
from core.models import TimeStampedModel, MoneyMixin
from documentos.models import Documento
from polizas.models import Poliza

# ---------------------------------------------------------------------
# Finanzas: Pagos / Comisiones (cuentas simples)
# ---------------------------------------------------------------------

class Pago(TimeStampedModel, MoneyMixin):
    class Estatus(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        VENCIDO = "VENCIDO", "Vencido"
        CANCELADO = "CANCELADO", "Cancelado"

    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, related_name="pagos")
    fecha_programada = models.DateField(db_index=True)
    fecha_pago = models.DateField(null=True, blank=True, db_index=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    metodo = models.CharField(max_length=40, blank=True, default="", db_index=True)
    referencia = models.CharField(max_length=80, blank=True, default="", db_index=True)
    estatus = models.CharField(max_length=10, choices=Estatus.choices, default=Estatus.PENDIENTE, db_index=True)
    comprobante = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos")

    class Meta:
        indexes = [
            models.Index(fields=["estatus", "fecha_programada"]),
            models.Index(fields=["poliza", "estatus"]),
        ]
        permissions = [
            ("manage_pagos", "Puede administrar pagos"),
        ]


class Comision(TimeStampedModel, MoneyMixin):
    class Estatus(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADA = "PAGADA", "Pagada"

    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, related_name="comisiones")
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comisiones")
    porcentaje = models.DecimalField(max_digits=6, decimal_places=3, default=0)  # 0-100
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estatus = models.CharField(max_length=10, choices=Estatus.choices, default=Estatus.PENDIENTE, db_index=True)
    fecha_pago = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["agente", "estatus"]),
            models.Index(fields=["poliza", "estatus"]),
        ]
        permissions = [
            ("manage_comisiones", "Puede administrar comisiones"),
        ]
