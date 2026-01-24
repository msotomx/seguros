from django.contrib import admin
from .models import (
    Marca,
    SubMarca,
    VehiculoCatalogo,
    Vehiculo,
    Conductor,
    Flotilla,
    FlotillaVehiculo,
)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "is_active", "created_at")
    search_fields = ("nombre",)
    list_filter = ("is_active",)
    ordering = ("nombre",)


@admin.register(SubMarca)
class SubMarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "marca", "is_active", "created_at")
    search_fields = ("nombre", "marca__nombre")
    list_filter = ("is_active", "marca")
    autocomplete_fields = ("marca",)
    list_select_related = ("marca",)
    ordering = ("marca__nombre", "nombre")


@admin.register(VehiculoCatalogo)
class VehiculoCatalogoAdmin(admin.ModelAdmin):
    list_display = ("marca", "submarca", "anio", "version", "clave_amis", "tipo_vehiculo", "valor_referencia", "is_active")
    search_fields = ("marca__nombre", "submarca__nombre", "version", "clave_amis", "tipo_vehiculo")
    list_filter = ("marca", "anio", "tipo_vehiculo", "is_active")
    autocomplete_fields = ("marca", "submarca")
    list_select_related = ("marca", "submarca")
    ordering = ("-anio", "marca__nombre", "submarca__nombre", "version")


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = (
        "cliente",
        "tipo_uso",
        "modelo_anio",
        "marca_texto",
        "submarca_texto",
        "tipo_vehiculo",
        "placas",
        "vin",
        "is_active",
        "created_at",
    )
    search_fields = (
        "cliente__nombre",
        "placas",
        "vin",
        "serie_motor",
        "marca_texto",
        "submarca_texto",
        "tipo_vehiculo",
        "catalogo__marca__nombre",
        "catalogo__submarca__nombre",
        "catalogo__clave_amis",
    )
    list_filter = ("is_active", "tipo_uso", "modelo_anio", "tipo_vehiculo", "created_at")
    autocomplete_fields = ("cliente", "catalogo")
    list_select_related = ("cliente", "catalogo")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    # Opcional (útil cuando usas SoftDelete/TimeStamped)
    readonly_fields = ("created_at", "updated_at")

    # Para que se vea más limpio al capturar
    fieldsets = (
        ("Cliente y uso", {"fields": ("cliente", "tipo_uso", "catalogo")}),
        ("Descripción", {"fields": ("marca_texto", "submarca_texto", "modelo_anio", "version", "tipo_vehiculo", "color")}),
        ("Identificadores", {"fields": ("vin", "serie_motor", "placas")}),
        ("Valor y notas", {"fields": ("valor_comercial", "adaptaciones", "is_active")}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cliente", "telefono", "email", "licencia_numero", "licencia_estado", "is_active", "created_at")
    search_fields = ("nombre", "telefono", "email", "licencia_numero", "cliente__nombre")
    list_filter = ("is_active", "licencia_estado", "created_at")
    autocomplete_fields = ("cliente",)
    list_select_related = ("cliente",)
    date_hierarchy = "created_at"
    ordering = ("cliente__nombre", "nombre")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Flotilla)
class FlotillaAdmin(admin.ModelAdmin):
    list_display = ("nombre_flotilla", "cliente", "is_active", "created_at")
    search_fields = ("nombre_flotilla", "cliente__nombre")
    list_filter = ("is_active", "created_at")
    autocomplete_fields = ("cliente",)
    list_select_related = ("cliente",)
    date_hierarchy = "created_at"
    ordering = ("cliente__nombre", "nombre_flotilla")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FlotillaVehiculo)
class FlotillaVehiculoAdmin(admin.ModelAdmin):
    list_display = ("flotilla", "vehiculo", "fecha_alta", "fecha_baja", "created_at")
    search_fields = (
        "flotilla__nombre_flotilla",
        "flotilla__cliente__nombre",
        "vehiculo__placas",
        "vehiculo__vin",
        "vehiculo__cliente__nombre",
    )
    list_filter = ("flotilla", "fecha_alta", "fecha_baja")
    autocomplete_fields = ("flotilla", "vehiculo")
    list_select_related = ("flotilla", "vehiculo")
    date_hierarchy = "fecha_alta"
    ordering = ("-fecha_alta",)
