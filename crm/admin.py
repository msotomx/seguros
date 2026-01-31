from django.contrib import admin
from .models import Direccion, Cliente, ClienteContacto, Conversacion, Mensaje


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("calle", "num_ext", "colonia", "ciudad", "estado", "cp", "pais")
    search_fields = ("calle", "num_ext", "num_int", "colonia", "ciudad", "estado", "cp", "pais")
    list_filter = ("estado", "ciudad", "pais")
    ordering = ("estado", "ciudad", "cp")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_cliente",
        "nombre_comercial",
        "nombre",
        "apellido_paterno",
        "rfc",
        "email_principal",
        "telefono_principal",
        "estatus",
        "origen",
        "owner",
        "is_active",
        "created_at",
        "user_portal",
        "portal_activo",
    )
    search_fields = (
        "nombre_comercial",
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "rfc",
        "curp",
        "email_principal",
        "telefono_principal",
        "origen",
    )
    list_filter = ("tipo_cliente", "estatus", "is_active", "origen", "created_at")
    autocomplete_fields = ("owner", "direccion_fiscal", "direccion_contacto")
    list_select_related = ("owner", "direccion_fiscal", "direccion_contacto")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Tipo de cliente", {"fields": ("tipo_cliente", "estatus", "origen", "owner", "is_active","user_portal","portal_activo")}),
        ("Datos generales", {"fields": ("nombre_comercial", "nombre", "apellido_paterno", "apellido_materno")}),
        ("Identificación", {"fields": ("rfc", "curp")}),
        ("Contacto", {"fields": ("email_principal", "telefono_principal")}),
        ("Direcciones", {"fields": ("direccion_fiscal", "direccion_contacto")}),
        ("Notas", {"fields": ("notas",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ClienteContacto)
class ClienteContactoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cliente", "rol", "telefono", "email", "preferido", "is_active", "created_at")
    search_fields = ("nombre", "rol", "telefono", "email", "cliente__nombre_comercial", "cliente__nombre", "cliente__rfc")
    list_filter = ("preferido", "is_active", "created_at")
    autocomplete_fields = ("cliente",)
    list_select_related = ("cliente",)
    date_hierarchy = "created_at"
    ordering = ("cliente__id", "preferido", "nombre")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "asunto",
        "canal_principal",
        "relacionado_tipo",
        "relacionado_id",
        "estatus",
        "owner",
        "updated_at",
    )
    search_fields = (
        "asunto",
        "cliente__nombre_comercial",
        "cliente__nombre",
        "cliente__apellido_paterno",
        "cliente__rfc",
        "relacionado_tipo",
    )
    list_filter = ("canal_principal", "estatus", "relacionado_tipo", "updated_at")
    autocomplete_fields = ("cliente", "owner")
    list_select_related = ("cliente", "owner")
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Cliente y estado", {"fields": ("cliente", "asunto", "canal_principal", "estatus", "owner")}),
        ("Relacionado (opcional)", {"fields": ("relacionado_tipo", "relacionado_id")}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ("id", "conversacion", "fecha_hora", "canal", "direccion", "usuario", "leido")
    search_fields = (
        "contenido",
        "conversacion__asunto",
        "conversacion__cliente__nombre_comercial",
        "conversacion__cliente__nombre",
        "conversacion__cliente__rfc",
        "usuario__username",
        "usuario__email",
        "archivo__nombre_archivo",
        "archivo__hash",
    )
    list_filter = ("canal", "direccion", "leido", "fecha_hora")
    autocomplete_fields = ("conversacion", "usuario", "archivo")
    list_select_related = ("conversacion", "usuario", "archivo")
    date_hierarchy = "fecha_hora"
    ordering = ("-fecha_hora",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Encabezado", {"fields": ("conversacion", "fecha_hora", "canal", "direccion", "usuario", "leido")}),
        ("Contenido", {"fields": ("contenido",)}),
        ("Adjunto / Metadata", {"fields": ("archivo", "metadata")}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )
