from django.conf import settings
from django.db import models
from core.models import TimeStampedModel, MoneyMixin
from documentos.models import Documento
from polizas.models import Poliza

# ---------------------------------------------------------------------
# Finanzas: Pagos / Comisiones (cuentas simples)
# ---------------------------------------------------------------------

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from documentos.models import Documento


class Pago(TimeStampedModel):
    class Estatus(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        PAGADO = "PAGADO", "Pagado"
        PARCIAL = "PARCIAL", "Parcial"
        VENCIDO = "VENCIDO", "Vencido"
        CANCELADO = "CANCELADO", "Cancelado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        PENDIENTE_REVISION = "PENDIENTE_REVISION", "Pendiente revisión"
        # ------------------------------------------------------------------
        # LOGICA EN ESTATUS:
        # PENDIENTE: recién creado, aún no inicia pago
        # EN_PROCESO: ya se generó checkout o provider lo tiene pending
        # PAGADO: pago conciliado correctamente
        # PARCIAL: pagó menos
        # VENCIDO: fecha vencida, pero aún puede pagarse si tú lo permites
        # RECHAZADO: provider lo rechazó
        # PENDIENTE_REVISION: diferencia de monto o inconsistencia
        # CANCELADO: anulado por negocio
        # ------------------------------------------------------------------

    class Provider(models.TextChoices):
        MERCADOPAGO = "MERCADOPAGO", "MercadoPago"
        STRIPE = "STRIPE", "Stripe"

    class Metodo(models.TextChoices):
        TARJETA = "TARJETA", "Tarjeta"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        EFECTIVO = "EFECTIVO", "Efectivo"
        SPEI = "SPEI", "SPEI"
        OXXO = "OXXO", "OXXO"
        MERCADOPAGO = "MERCADOPAGO", "MercadoPago"
        OTRO = "OTRO", "Otro"

    poliza = models.ForeignKey(
        "polizas.Poliza",
        on_delete=models.CASCADE,
        related_name="pagos",
        null=True,
        blank=True,
    )

    cliente = models.ForeignKey(
        "crm.Cliente",
        on_delete=models.CASCADE,
        related_name="pagos",
        null=True,
        blank=True,
    )

    usuario_portal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pagos_portal",
        null=True,
        blank=True,
    )

    concepto = models.CharField(max_length=200, blank=True, default="")
    descripcion = models.TextField(blank=True, default="")

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Monto esperado del pago.",
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Monto efectivamente pagado/conciliado por el provider.",
    )
    moneda = models.CharField(max_length=10, default="MXN")
    comision_provider = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    estatus = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.PENDIENTE,
        db_index=True,
    )

    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
        blank=True,
        null=True,
        db_index=True,
    )
    provider_payment_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
        help_text="ID del pago devuelto por el provider.",
    )
    provider_preference_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
        help_text="ID del checkout/preference/intent del provider.",
    )
    provider_status = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        db_index=True,
        help_text="Estatus técnico devuelto por el provider (approved, pending, rejected, etc.).",
    )

    metodo = models.CharField(
        max_length=30,
        choices=Metodo.choices,
        blank=True,
        null=True,
    )
    referencia = models.CharField(
        max_length=120,
        blank=True,
        default="",
        db_index=True,
        help_text="Referencia visible o interna del pago.",
    )

    # fecha_programada: día en que debe cobrarse o publicarse
    # fecha_vencimiento: último día permitido sin atraso
    # fecha_pago: día en que se pagó

    fecha_programada = models.DateField(db_index=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_pago = models.DateField(null=True, blank=True)
    fecha_pago_provider = models.DateTimeField(null=True, blank=True)

    checkout_url = models.URLField(blank=True, null=True)

    comprobante = models.ForeignKey(
        Documento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos",
    )

    webhook_last_payload = models.JSONField(default=dict, blank=True)
    payload_resumen_json = models.JSONField(default=dict, blank=True)

    observaciones = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["estatus", "fecha_pago"]),
            models.Index(fields=["provider", "provider_payment_id"]),
            models.Index(fields=["provider_preference_id"]),
            models.Index(fields=["referencia"]),
            models.Index(fields=["fecha_programada"]),
        ]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        base = f"Pago #{self.pk}"
        if self.poliza_id:
            base += f" | Póliza #{self.poliza_id}"
        return f"{base} | {self.estatus}"

    @property
    def monto_pendiente(self):
        pagado = self.monto_pagado or Decimal("0.00")
        pendiente = self.monto - pagado
        return pendiente if pendiente > 0 else Decimal("0.00")

    @property
    def esta_vencido(self):
        if self.fecha_vencimiento:
            return self.fecha_vencimiento < timezone.localdate()
        return False

    def puede_generar_checkout(self):
        return self.estatus in {
            self.Estatus.PENDIENTE,
            self.Estatus.EN_PROCESO,
            self.Estatus.VENCIDO,
            self.Estatus.PENDIENTE_REVISION,
        }

    def marcar_como_pagado_localmente(
        self,
        *,
        amount=None,
        metodo=None,
        referencia=None,
        provider=None,
        provider_payment_id=None,
        provider_status=None,
        fecha_pago_provider=None,
        payload=None,
    ):
        self.estatus = self.Estatus.PAGADO
        self.fecha_pago = timezone.localdate()

        if amount is not None:
            self.monto_pagado = amount
        if metodo:
            self.metodo = metodo
        if referencia:
            self.referencia = referencia
        if provider:
            self.provider = provider
        if provider_payment_id:
            self.provider_payment_id = provider_payment_id
        if provider_status:
            self.provider_status = provider_status
        if fecha_pago_provider:
            self.fecha_pago_provider = fecha_pago_provider
        if payload:
            self.webhook_last_payload = payload
        if payload:
            self.payload_resumen_json = payload

# ------------------------------------------------------------------------
# PagoTransaccion: 
# Este modelo guarda cada interacción importante:
# -checkout creado
# -webhook recibido
# -approved
# -rejected
# -conciliación ok
# -conciliación error
#----------------------------------------------------------------------------
class PagoTransaccion(TimeStampedModel):
    class Tipo(models.TextChoices):
        CHECKOUT_CREADO = "CHECKOUT_CREADO", "Checkout creado"
        WEBHOOK_RECIBIDO = "WEBHOOK_RECIBIDO", "Webhook recibido"
        PAYMENT_APPROVED = "PAYMENT_APPROVED", "Payment approved"
        PAYMENT_REJECTED = "PAYMENT_REJECTED", "Payment rejected"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment pending"
        RECONCILIACION_OK = "RECONCILIACION_OK", "Conciliación OK"
        RECONCILIACION_ERROR = "RECONCILIACION_ERROR", "Conciliación error"

    pago = models.ForeignKey(
        "finanzas.Pago",
        on_delete=models.CASCADE,
        related_name="transacciones",
    )

    provider = models.CharField(max_length=30, db_index=True)
    tipo = models.CharField(
        max_length=40,
        choices=Tipo.choices,
        db_index=True,
    )

    provider_payment_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
    )
    provider_preference_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
    )
    provider_status = models.CharField(
        max_length=60,
        blank=True,
        null=True,
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    moneda = models.CharField(max_length=10, default="MXN")

    payload = models.JSONField(default=dict, blank=True)
    observaciones = models.TextField(blank=True, default="")

    procesado = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["provider", "provider_payment_id"]),
            models.Index(fields=["provider", "provider_preference_id"]),
            models.Index(fields=["tipo", "created_at"]),
        ]
        verbose_name = "Transacción de pago"
        verbose_name_plural = "Transacciones de pago"

    def __str__(self):
        return f"Tx #{self.pk} | Pago #{self.pago_id} | {self.tipo}"


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
