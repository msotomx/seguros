from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.db.models.constraints import UniqueConstraint
from core.models import TimeStampedModel, SoftDeleteModel
from crm.models import Cliente

# ---------------------------------------------------------------------
# Autos: Vehículos / Conductores / Flotillas + Catálogo (opcional)
# ---------------------------------------------------------------------

class Marca(TimeStampedModel, SoftDeleteModel):
    nombre = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.nombre


class SubMarca(TimeStampedModel, SoftDeleteModel):
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE, related_name="submarcas")
    nombre = models.CharField(max_length=120)

    class Meta:
        constraints = [UniqueConstraint(fields=["marca", "nombre"], name="uq_marca_submarca")]

    def __str__(self):
        return f"{self.marca.nombre} {self.nombre}"


class VehiculoCatalogo(TimeStampedModel, SoftDeleteModel):
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name="vehiculos_catalogo")
    submarca = models.ForeignKey(SubMarca, on_delete=models.PROTECT, related_name="vehiculos_catalogo")
    anio = models.PositiveIntegerField(validators=[MinValueValidator(1950), MaxValueValidator(2100)], db_index=True)
    version = models.CharField(max_length=120, blank=True, default="")
    clave_amis = models.CharField(max_length=40, blank=True, default="", db_index=True)
    tipo_vehiculo = models.CharField(max_length=50, blank=True, default="", db_index=True)
    valor_referencia = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["marca", "submarca", "anio"]),
            models.Index(fields=["clave_amis"]),
        ]


class Vehiculo(TimeStampedModel, SoftDeleteModel):
    class TipoUso(models.TextChoices):
        PARTICULAR = "PARTICULAR", "Particular"
        COMERCIAL = "COMERCIAL", "Comercial"
        PLATAFORMA = "PLATAFORMA", "Plataforma (Uber/Didi)"
        CARGA = "CARGA", "Carga"
        OTRO = "OTRO", "Otro"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="vehiculos")
    catalogo = models.ForeignKey(VehiculoCatalogo, on_delete=models.SET_NULL, null=True, blank=True, related_name="vehiculos")
    tipo_uso = models.CharField(max_length=15, choices=TipoUso.choices, default=TipoUso.PARTICULAR, db_index=True)

    marca_texto = models.CharField(max_length=120, blank=True, default="")
    submarca_texto = models.CharField(max_length=120, blank=True, default="")
    modelo_anio = models.PositiveIntegerField(validators=[MinValueValidator(1950), MaxValueValidator(2100)], db_index=True)
    version = models.CharField(max_length=120, blank=True, default="")

    vin = models.CharField(max_length=40, blank=True, default="", db_index=True)
    serie_motor = models.CharField(max_length=40, blank=True, default="")
    placas = models.CharField(max_length=20, blank=True, default="", db_index=True)
    color = models.CharField(max_length=40, blank=True, default="")
    tipo_vehiculo = models.CharField(max_length=50, blank=True, default="", db_index=True)
    valor_comercial = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    adaptaciones = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "is_active"]),
            models.Index(fields=["modelo_anio", "tipo_uso"]),
        ]
        permissions = [
            ("manage_vehiculos", "Puede administrar vehículos"),
        ]

    def __str__(self):
        return f"{self.marca_texto or (self.catalogo.marca.nombre if self.catalogo else '')} {self.submarca_texto or (self.catalogo.submarca.nombre if self.catalogo else '')} {self.modelo_anio}"


class Conductor(TimeStampedModel, SoftDeleteModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="conductores")
    nombre = models.CharField(max_length=200)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    licencia_numero = models.CharField(max_length=40, blank=True, default="", db_index=True)
    licencia_estado = models.CharField(max_length=100, blank=True, default="")
    telefono = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    notas = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["cliente", "is_active"])]

    def __str__(self):
        return self.nombre


class Flotilla(TimeStampedModel, SoftDeleteModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="flotillas")
    nombre_flotilla = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default="")

    class Meta:
        constraints = [UniqueConstraint(fields=["cliente", "nombre_flotilla"], name="uq_cliente_flotilla")]
        indexes = [models.Index(fields=["cliente", "is_active"])]

    def __str__(self):
        return f"{self.nombre_flotilla} - {self.cliente}"


class FlotillaVehiculo(TimeStampedModel):
    flotilla = models.ForeignKey(Flotilla, on_delete=models.CASCADE, related_name="items")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name="flotillas")
    fecha_alta = models.DateField(default=timezone.now)
    fecha_baja = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["flotilla", "vehiculo"], name="uq_flotilla_vehiculo")]
