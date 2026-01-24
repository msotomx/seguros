# models.py (Django + PostgreSQL, single-empresa, con permisos por usuario)
# Requiere: PostgreSQL (para JSONField y constraints), Django 4+ recomendado.

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint, CheckConstraint
from django.utils import timezone


# ---------------------------------------------------------------------
# Base / Utilidades
# ---------------------------------------------------------------------

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


class MoneyMixin(models.Model):
    # Si manejas multi-moneda, agrega moneda. Si no, puedes fijarla a MXN.
    moneda = models.CharField(max_length=3, default="MXN", db_index=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------
# Seguridad / Usuarios (Permisos por usuario)
# ---------------------------------------------------------------------
# Nota: Django ya trae permisos por modelo (add/change/delete/view) y grupos.
# Aquí agregamos un perfil y algunas banderas opcionales, además de permisos custom.

class UserProfile(TimeStampedModel):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        AGENTE = "AGENTE", "Agente"
        OPERADOR = "OPERADOR", "Operador"
        LECTURA = "LECTURA", "Solo lectura"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.AGENTE, db_index=True)
    telefono = models.CharField(max_length=30, blank=True, default="")
    notas = models.TextField(blank=True, default="")
    activo = models.BooleanField(default=True, db_index=True)

    # Alcance opcional (si quieres restringir qué aseguradoras ve un usuario)
    aseguradoras_permitidas = models.ManyToManyField(
        "Aseguradora", blank=True, related_name="usuarios_permitidos"
    )

    class Meta:
        permissions = [
            # permisos “de negocio” (además de add/change/delete/view)
            ("can_quote", "Puede cotizar"),
            ("can_issue_policy", "Puede emitir póliza"),
            ("can_cancel_policy", "Puede cancelar póliza"),
            ("can_manage_tariffs", "Puede administrar tarifas y reglas"),
            ("can_view_finance", "Puede ver finanzas (pagos/comisiones)"),
            ("can_manage_finance", "Puede administrar finanzas (pagos/comisiones)"),
        ]


# ---------------------------------------------------------------------
# Documentos / Archivos (adjuntos)
# ---------------------------------------------------------------------

class Documento(TimeStampedModel):
    class Tipo(models.TextChoices):
        PDF = "PDF", "PDF"
        IMG = "IMG", "Imagen"
        XML = "XML", "XML"
        DOC = "DOC", "Documento"
        OTRO = "OTRO", "Otro"

    nombre_archivo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.OTRO, db_index=True)
    file = models.FileField(upload_to="docs/%Y/%m/")
    tamano = models.PositiveIntegerField(default=0)
    hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos_subidos"
    )

    class Meta:
        permissions = [
            ("download_documento", "Puede descargar documentos"),
        ]


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


# ---------------------------------------------------------------------
# CRM: Clientes / Contactos / Direcciones
# ---------------------------------------------------------------------

class Direccion(TimeStampedModel):
    calle = models.CharField(max_length=200, blank=True, default="")
    num_ext = models.CharField(max_length=20, blank=True, default="")
    num_int = models.CharField(max_length=20, blank=True, default="")
    colonia = models.CharField(max_length=150, blank=True, default="")
    ciudad = models.CharField(max_length=150, blank=True, default="")
    estado = models.CharField(max_length=150, blank=True, default="")
    cp = models.CharField(max_length=10, blank=True, default="", db_index=True)
    pais = models.CharField(max_length=80, blank=True, default="México")
    referencias = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.calle} {self.num_ext} {self.colonia} {self.ciudad} {self.estado} {self.cp}"


class Cliente(TimeStampedModel, SoftDeleteModel):
    class TipoCliente(models.TextChoices):
        PERSONA = "PERSONA", "Persona"
        EMPRESA = "EMPRESA", "Empresa"

    class Estatus(models.TextChoices):
        PROSPECTO = "PROSPECTO", "Prospecto"
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"

    tipo_cliente = models.CharField(max_length=10, choices=TipoCliente.choices, db_index=True)
    nombre_comercial = models.CharField(max_length=200, blank=True, default="")  # empresas
    nombre = models.CharField(max_length=120, blank=True, default="")            # persona
    apellido_paterno = models.CharField(max_length=120, blank=True, default="")
    apellido_materno = models.CharField(max_length=120, blank=True, default="")
    rfc = models.CharField(max_length=20, blank=True, default="", db_index=True)
    curp = models.CharField(max_length=25, blank=True, default="")
    email_principal = models.EmailField(blank=True, default="", db_index=True)
    telefono_principal = models.CharField(max_length=30, blank=True, default="", db_index=True)
    direccion_fiscal = models.ForeignKey(Direccion, on_delete=models.SET_NULL, null=True, blank=True, related_name="clientes_fiscal")
    direccion_contacto = models.ForeignKey(Direccion, on_delete=models.SET_NULL, null=True, blank=True, related_name="clientes_contacto")
    estatus = models.CharField(max_length=12, choices=Estatus.choices, default=Estatus.PROSPECTO, db_index=True)
    origen = models.CharField(max_length=80, blank=True, default="", db_index=True)
    notas = models.TextField(blank=True, default="")
    owner = models.ForeignKey(  # para permisos “por usuario” (asignación de cartera)
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="clientes_asignados"
    )

    class Meta:
        indexes = [
            models.Index(fields=["tipo_cliente", "estatus", "is_active"]),
            models.Index(fields=["owner", "is_active"]),
        ]
        permissions = [
            ("manage_clientes", "Puede administrar clientes"),
            ("reassign_cliente_owner", "Puede reasignar cartera de clientes"),
        ]

    def __str__(self):
        if self.tipo_cliente == self.TipoCliente.EMPRESA:
            return self.nombre_comercial or f"Empresa #{self.pk}"
        return " ".join([p for p in [self.nombre, self.apellido_paterno, self.apellido_materno] if p]).strip() or f"Cliente #{self.pk}"


class ClienteContacto(TimeStampedModel, SoftDeleteModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contactos")
    nombre = models.CharField(max_length=200)
    rol = models.CharField(max_length=120, blank=True, default="")
    telefono = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    preferido = models.BooleanField(default=False)
    notas = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["cliente", "is_active"])]

    def __str__(self):
        return f"{self.nombre} - {self.cliente}"


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


# ---------------------------------------------------------------------
# Mensajería / CRM (historial con el cliente)
# ---------------------------------------------------------------------

class Conversacion(TimeStampedModel):
    class Canal(models.TextChoices):
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL = "EMAIL", "Email"
        LLAMADA = "LLAMADA", "Llamada"
        SMS = "SMS", "SMS"
        PRESENCIAL = "PRESENCIAL", "Presencial"
        OTRO = "OTRO", "Otro"

    class Estatus(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="conversaciones")
    asunto = models.CharField(max_length=200)
    canal_principal = models.CharField(max_length=12, choices=Canal.choices, default=Canal.WHATSAPP, db_index=True)

    # Para relacionar con cotización/póliza/siniestro sin GenericFK (simple)
    relacionado_tipo = models.CharField(max_length=20, blank=True, default="", db_index=True)  # "COTIZACION", "POLIZA", "SINIESTRO"
    relacionado_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    estatus = models.CharField(max_length=10, choices=Estatus.choices, default=Estatus.ABIERTA, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversaciones")

    class Meta:
        indexes = [models.Index(fields=["cliente", "estatus", "updated_at"])]


class Mensaje(TimeStampedModel):
    class Direccion(models.TextChoices):
        SALIENTE = "SALIENTE", "Saliente"
        ENTRANTE = "ENTRANTE", "Entrante"

    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="mensajes")
    fecha_hora = models.DateTimeField(default=timezone.now, db_index=True)
    canal = models.CharField(max_length=12, choices=Conversacion.Canal.choices, db_index=True)
    direccion = models.CharField(max_length=10, choices=Direccion.choices, db_index=True)
    contenido = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensajes")
    archivo = models.ForeignKey(Documento, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensajes")
    leido = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["conversacion", "fecha_hora"])]


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
    modo_aplicacion = models.CharField(max_length=16, choices=ModoAplicacion.choices, default=ModoAplicacion.PRIMER_MATCH)
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


# ---------------------------------------------------------------------
# Cotizaciones / Comparativos (A + B)
# ---------------------------------------------------------------------

class Cotizacion(TimeStampedModel):
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

    tipo_cotizacion = models.CharField(max_length=10, choices=Tipo.choices, db_index=True)
    vigencia_desde = models.DateField(db_index=True)
    vigencia_hasta = models.DateField(db_index=True)

    forma_pago_preferida = models.CharField(max_length=30, blank=True, default="", db_index=True)
    notas = models.TextField(blank=True, default="")
    estatus = models.CharField(max_length=10, choices=Estatus.choices, default=Estatus.BORRADOR, db_index=True)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="cotizaciones")

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

