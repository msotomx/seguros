from django.db import models
from django.db.models.constraints import UniqueConstraint
from core.models import TimeStampedModel, SoftDeleteModel, MoneyMixin

# ---------------------------------------------------------------------
# Catálogos: Aseguradoras / Productos / Coberturas
# ---------------------------------------------------------------------

class Aseguradora(TimeStampedModel, SoftDeleteModel):
    nombre = models.CharField(max_length=200, unique=True)
    rfc = models.CharField(max_length=20, blank=True, default="")
    sitio_web = models.URLField(blank=True, default="")
    telefono_contacto = models.CharField(max_length=30, blank=True, default="")
    email_contacto = models.EmailField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["is_active", "nombre"])]
        permissions = [
            ("manage_aseguradora", "Puede administrar aseguradoras"),
        ]

    def __str__(self):
        return self.nombre


class AseguradoraContacto(TimeStampedModel, SoftDeleteModel):
    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.CASCADE, related_name="contactos")
    nombre = models.CharField(max_length=200)
    puesto = models.CharField(max_length=150, blank=True, default="")
    telefono = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    notas = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["aseguradora", "is_active"])]

    def __str__(self):
        return f"{self.nombre} ({self.aseguradora.nombre})"


class ProductoSeguro(TimeStampedModel, SoftDeleteModel, MoneyMixin):
    class TipoProducto(models.TextChoices):
        AUTO = "AUTO", "Auto"
        FLOTILLA = "FLOTILLA", "Flotilla"
        MOTO = "MOTO", "Moto"
        OTRO = "OTRO", "Otro"

    class ModeloCalculo(models.TextChoices):
        SIMPLE = "SIMPLE", "Captura externa (A)"
        REGLAS = "REGLAS", "Motor de reglas (B)"

    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.CASCADE, related_name="productos")
    nombre_producto = models.CharField(max_length=200)
    tipo_producto = models.CharField(max_length=20, choices=TipoProducto.choices, default=TipoProducto.AUTO, db_index=True)
    descripcion = models.TextField(blank=True, default="")
    modelo_calculo = models.CharField(max_length=10, choices=ModeloCalculo.choices, default=ModeloCalculo.REGLAS, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["aseguradora", "nombre_producto"], name="uq_producto_por_aseguradora"),
        ]
        indexes = [
            models.Index(fields=["aseguradora", "is_active"]),
            models.Index(fields=["tipo_producto", "is_active"]),
        ]
        permissions = [
            ("manage_producto_seguro", "Puede administrar productos/planes"),
        ]

    def __str__(self):
        return f"{self.aseguradora.nombre} - {self.nombre_producto}"


class CoberturaCatalogo(TimeStampedModel, SoftDeleteModel):
    class TipoValor(models.TextChoices):
        MONTO = "MONTO", "Monto"
        PORCENTAJE = "PORCENTAJE", "Porcentaje"
        TEXTO = "TEXTO", "Texto"
        BOOL = "BOOL", "Sí/No"

    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default="")
    tipo_valor = models.CharField(max_length=15, choices=TipoValor.choices, default=TipoValor.MONTO, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["is_active", "codigo"])]
        permissions = [
            ("manage_coberturas", "Puede administrar catálogo de coberturas"),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ProductoCobertura(TimeStampedModel):
    producto = models.ForeignKey(ProductoSeguro, on_delete=models.CASCADE, related_name="coberturas")
    cobertura = models.ForeignKey(CoberturaCatalogo, on_delete=models.CASCADE, related_name="productos")
    incluida = models.BooleanField(default=True)
    valor_default = models.CharField(max_length=120, blank=True, default="")
    notas = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["producto", "cobertura"], name="uq_producto_cobertura"),
        ]
