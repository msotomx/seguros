from django.db import models
from django.db.models.constraints import UniqueConstraint
from core.models import TimeStampedModel, SoftDeleteModel
from catalogos.models import Aseguradora, ProductoSeguro, CoberturaCatalogo  # ver nota abajo


# Create your models here.
# ---------------------------------------------------------------------
# Motor de Tarifas (B): Zonas / Variables / Tablas / Reglas
# ---------------------------------------------------------------------

class ZonaTarifa(TimeStampedModel, SoftDeleteModel):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ZonaTarifaDetalle(TimeStampedModel):
    zona = models.ForeignKey(ZonaTarifa, on_delete=models.CASCADE, related_name="detalles")
    pais = models.CharField(max_length=80, blank=True, default="México")
    estado = models.CharField(max_length=150, blank=True, default="")
    ciudad = models.CharField(max_length=150, blank=True, default="")
    cp_inicio = models.CharField(max_length=10, blank=True, default="")
    cp_fin = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["zona", "estado", "ciudad"]),
            models.Index(fields=["cp_inicio", "cp_fin"]),
        ]


class VariableTarifa(TimeStampedModel, SoftDeleteModel):
    class TipoDato(models.TextChoices):
        INT = "INT", "Entero"
        DECIMAL = "DECIMAL", "Decimal"
        TEXT = "TEXT", "Texto"
        BOOL = "BOOL", "Sí/No"
        DATE = "DATE", "Fecha"

    class Origen(models.TextChoices):
        CLIENTE = "CLIENTE", "Cliente"
        VEHICULO = "VEHICULO", "Vehículo"
        CONDUCTOR = "CONDUCTOR", "Conductor"
        COTIZACION = "COTIZACION", "Cotización"
        SISTEMA = "SISTEMA", "Sistema"

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=120)
    tipo_dato = models.CharField(max_length=10, choices=TipoDato.choices, db_index=True)
    origen = models.CharField(max_length=12, choices=Origen.choices, db_index=True)
    descripcion = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["is_active", "origen", "codigo"])]


class TablaFactor(TimeStampedModel, SoftDeleteModel):
    class Tipo(models.TextChoices):
        FACTOR = "FACTOR", "Factor"
        MONTO = "MONTO", "Monto"
        PORCENTAJE = "PORCENTAJE", "Porcentaje"

    nombre = models.CharField(max_length=150, unique=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.FACTOR, db_index=True)
    descripcion = models.TextField(blank=True, default="")

    def __str__(self):
        return self.nombre


class TablaFactorRango(TimeStampedModel, SoftDeleteModel):
    tabla = models.ForeignKey(TablaFactor, on_delete=models.CASCADE, related_name="rangos")
    var1 = models.ForeignKey(VariableTarifa, on_delete=models.PROTECT, related_name="tabla_rango_var1")
    var1_min = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    var1_max = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    var2 = models.ForeignKey(VariableTarifa, on_delete=models.PROTECT, null=True, blank=True, related_name="tabla_rango_var2")
    var2_min = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    var2_max = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    valor = models.DecimalField(max_digits=14, decimal_places=6)  # factor/monto/%
    prioridad = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["tabla", "is_active", "prioridad"]),
            models.Index(fields=["var1", "var2"]),
        ]


class ReglaTarifa(TimeStampedModel, SoftDeleteModel):
    class TipoRegla(models.TextChoices):
        ELEGIBILIDAD = "ELEGIBILIDAD", "Elegibilidad"
        PRIMA_BASE = "PRIMA_BASE", "Prima base"
        FACTOR = "FACTOR", "Factor"
        RECARGO = "RECARGO", "Recargo"
        DESCUENTO = "DESCUENTO", "Descuento"
        DERECHOS = "DERECHOS", "Derechos"
        AJUSTE_COBERTURA = "AJUSTE_COBERTURA", "Ajuste cobertura"

    class ModoAplicacion(models.TextChoices):
        PRIMER_MATCH = "PRIMER_MATCH", "Primer match"
        SUMAR_TODAS = "SUMAR_TODAS", "Sumar todas"
        MULTIPLICAR_TODAS = "MULTIPLICAR_TODAS", "Multiplicar todas"

    producto = models.ForeignKey(ProductoSeguro, on_delete=models.CASCADE, related_name="reglas")
    nombre = models.CharField(max_length=200)
    tipo_regla = models.CharField(max_length=20, choices=TipoRegla.choices, db_index=True)
    modo_aplicacion = models.CharField(max_length=20, choices=ModoAplicacion.choices, default=ModoAplicacion.PRIMER_MATCH)
    prioridad = models.IntegerField(default=0, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["producto", "tipo_regla", "prioridad", "is_active"])]
        permissions = [
            ("manage_reglas_tarifa", "Puede administrar reglas de tarifa"),
        ]


class ReglaCondicion(TimeStampedModel):
    class Operador(models.TextChoices):
        EQ = "=", "="
        NE = "!=", "!="
        GT = ">", ">"
        GE = ">=", ">="
        LT = "<", "<"
        LE = "<=", "<="
        IN = "IN", "IN"
        NOT_IN = "NOT_IN", "NOT IN"
        BETWEEN = "BETWEEN", "BETWEEN"
        CONTAINS = "CONTAINS", "CONTAINS"

    regla = models.ForeignKey(ReglaTarifa, on_delete=models.CASCADE, related_name="condiciones")
    variable = models.ForeignKey(VariableTarifa, on_delete=models.PROTECT, related_name="condiciones")
    operador = models.CharField(max_length=10, choices=Operador.choices)
    valor1 = models.CharField(max_length=200)
    valor2 = models.CharField(max_length=200, blank=True, default="")
    negada = models.BooleanField(default=False)
    grupo = models.PositiveIntegerField(default=1, db_index=True)
    orden = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["regla", "grupo", "orden"])]


class ReglaAccion(TimeStampedModel):
    class TipoAccion(models.TextChoices):
        SET_MONTO = "SET_MONTO", "Set monto"
        SET_FACTOR = "SET_FACTOR", "Set factor"
        SUMAR_MONTO = "SUMAR_MONTO", "Sumar monto"
        APLICAR_TABLA_FACTOR = "APLICAR_TABLA_FACTOR", "Aplicar tabla factor"
        SET_PORCENTAJE = "SET_PORCENTAJE", "Set %"
        RECHAZAR = "RECHAZAR", "Rechazar"

    class Redondeo(models.TextChoices):
        NO = "NO", "No"
        DOS_DEC = "2_DEC", "2 dec"
        ENTERO = "ENTERO", "Entero"

    regla = models.ForeignKey(ReglaTarifa, on_delete=models.CASCADE, related_name="acciones")
    tipo_accion = models.CharField(max_length=22, choices=TipoAccion.choices, db_index=True)
    variable_destino = models.CharField(max_length=50, blank=True, default="", db_index=True)  # ej: "prima_base", "derechos", etc.
    valor = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    valor_texto = models.CharField(max_length=200, blank=True, default="")
    tabla_factor = models.ForeignKey(TablaFactor, on_delete=models.PROTECT, null=True, blank=True, related_name="acciones")
    redondeo = models.CharField(max_length=10, choices=Redondeo.choices, default=Redondeo.NO)
    minimo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    maximo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    orden = models.PositiveIntegerField(default=1, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["regla", "orden"])]


class CoberturaTarifa(TimeStampedModel, SoftDeleteModel):
    class ModoCosto(models.TextChoices):
        FIJO = "FIJO", "Fijo"
        PORC_PRIMA_BASE = "PORC_PRIMA_BASE", "% prima base"
        PORC_VALOR_VEH = "PORC_VALOR_VEH", "% valor veh"
        TABLA_FACTOR = "TABLA_FACTOR", "Tabla factor"

    producto = models.ForeignKey(ProductoSeguro, on_delete=models.CASCADE, related_name="coberturas_tarifa")
    cobertura = models.ForeignKey(CoberturaCatalogo, on_delete=models.PROTECT, related_name="tarifas")
    modo_costo = models.CharField(max_length=20, choices=ModoCosto.choices, db_index=True)
    monto_fijo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    porcentaje = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)  # 0-100
    tabla_factor = models.ForeignKey(TablaFactor, on_delete=models.PROTECT, null=True, blank=True, related_name="coberturas")
    minimo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    maximo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["producto", "cobertura"], name="uq_producto_cobertura_tarifa")]


class DeducibleOpcion(TimeStampedModel, SoftDeleteModel):
    class Tipo(models.TextChoices):
        DM = "DM", "Daños materiales"
        RT = "RT", "Robo total"
        RC = "RC", "Resp. civil"
        OTRO = "OTRO", "Otro"

    producto = models.ForeignKey(ProductoSeguro, on_delete=models.CASCADE, related_name="deducibles")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, db_index=True)
    valor = models.DecimalField(max_digits=12, decimal_places=4)  # porcentaje o monto
    es_porcentaje = models.BooleanField(default=True)
    afecta_prima = models.BooleanField(default=True)
    factor_prima = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["producto", "tipo", "is_active"])]
