from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel, SoftDeleteModel
from documentos.models import Documento

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
    apellido_paterno = models.CharField(max_length=50, blank=True, default="")
    apellido_materno = models.CharField(max_length=50, blank=True, default="")
    contacto_nombre = models.CharField(max_length=50, blank=True, default="")
    contacto_email = models.EmailField(blank=True, default="")
    contacto_telefono = models.CharField(max_length=30, blank=True, default="")
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
    user_portal = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cliente_portal",
    )
    portal_activo = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["tipo_cliente", "estatus", "is_active"]),
            models.Index(fields=["owner", "is_active"]),
        ]
        permissions = [
            ("manage_clientes", "Puede administrar clientes"),
            ("reassign_cliente_owner", "Puede reasignar cartera de clientes"),
            ("manage_portal_activo", "Puede activar/desactivar portal de clientes"),

        ]
    @property
    def nombre_mostrar(self):
        partes = [
            self.nombre or "",
            self.apellido_paterno or "",
            self.apellido_materno or "",
        ]

        nombre_completo = " ".join(p.strip() for p in partes if p and p.strip())

        if nombre_completo:
            return nombre_completo

        return self.nombre_comercial or ""


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

