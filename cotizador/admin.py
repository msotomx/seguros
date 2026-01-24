from django.contrib import admin
from .models import (
    Cotizacion,
    CotizacionItem,
    CotizacionItemCobertura,
    CotizacionItemCalculo,
    CotizacionItemReglaAplicada,
    CotizacionFlotillaItemVehiculo,
)


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "tipo_cotizacion",
        "vehiculo",
        "flotilla",
        "vigencia_desde",
        "vigencia_hasta",
        "estatus",
        "owner",
        "created_at",
    )
    search_fields = (
        "cliente__nombre_comercial",
        "cliente__nombre",
        "cliente__apellido_paterno",
        "cliente__rfc",
        "owner__username",
        "owner__email",
        "forma_pago_preferida",
    )
    list_filter = ("tipo_cotizacion", "estatus", "vigencia_desde", "vigencia_hasta", "created_at")
    autocomplete_fields = ("cliente", "vehiculo", "flotilla", "owner")
    list_select_related = ("cliente", "vehiculo", "flotilla", "owner")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Cliente y tipo", {"fields": ("cliente", "tipo_cotizacion", "vehiculo", "flotilla")}),
        ("Vigencia", {"fields": ("vigencia_desde", "vigencia_hasta")}),
        ("Estatus y asignación", {"fields": ("estatus", "owner")}),
        ("Preferencias", {"fields": ("forma_pago_preferida",)}),
        ("Notas", {"fields": ("notas",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CotizacionItem)
class CotizacionItemAdmin(admin.ModelAdmin):
    list_display = (
        "cotizacion",
        "aseguradora",
        "producto",
        "ranking",
        "seleccionada",
        "prima_neta",
        "derechos",
        "recargos",
        "descuentos",
        "iva",
        "prima_total",
        "forma_pago",
        "meses",
        "created_at",
    )
    search_fields = (
        "cotizacion__id",
        "aseguradora__nombre",
        "producto__nombre_producto",
        "producto__aseguradora__nombre",
        "forma_pago",
        "observaciones",
    )
    list_filter = ("seleccionada", "aseguradora", "producto", "forma_pago", "meses", "created_at")
    autocomplete_fields = ("cotizacion", "aseguradora", "producto")
    list_select_related = ("cotizacion", "aseguradora", "producto")
    ordering = ("cotizacion_id", "ranking", "-prima_total")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Relación", {"fields": ("cotizacion", "aseguradora", "producto")}),
        ("Resultados", {"fields": ("prima_neta", "derechos", "recargos", "descuentos", "iva", "prima_total")}),
        ("Pago / ranking", {"fields": ("forma_pago", "meses", "ranking", "seleccionada")}),
        ("Notas", {"fields": ("observaciones",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CotizacionItemCobertura)
class CotizacionItemCoberturaAdmin(admin.ModelAdmin):
    list_display = ("item", "cobertura", "incluida", "valor", "created_at")
    search_fields = (
        "item__cotizacion__id",
        "item__aseguradora__nombre",
        "item__producto__nombre_producto",
        "cobertura__codigo",
        "cobertura__nombre",
        "valor",
    )
    list_filter = ("incluida", "cobertura", "created_at")
    autocomplete_fields = ("item", "cobertura")
    list_select_related = ("item", "cobertura")
    ordering = ("item_id", "cobertura_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CotizacionItemCalculo)
class CotizacionItemCalculoAdmin(admin.ModelAdmin):
    list_display = ("item", "prima_base", "factor_total", "created_at")
    search_fields = (
        "item__cotizacion__id",
        "item__aseguradora__nombre",
        "item__producto__nombre_producto",
    )
    list_filter = ("created_at",)
    autocomplete_fields = ("item",)
    list_select_related = ("item",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CotizacionItemReglaAplicada)
class CotizacionItemReglaAplicadaAdmin(admin.ModelAdmin):
    list_display = ("item", "orden", "regla", "resultado", "valor_resultante", "created_at")
    search_fields = (
        "item__cotizacion__id",
        "item__aseguradora__nombre",
        "item__producto__nombre_producto",
        "regla__id",
        "mensaje",
        "valor_resultante",
    )
    list_filter = ("resultado", "created_at")
    autocomplete_fields = ("item", "regla")
    list_select_related = ("item", "regla")
    ordering = ("item_id", "orden")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CotizacionFlotillaItemVehiculo)
class CotizacionFlotillaItemVehiculoAdmin(admin.ModelAdmin):
    list_display = ("item", "vehiculo", "prima_total", "created_at")
    search_fields = (
        "item__cotizacion__id",
        "vehiculo__placas",
        "vehiculo__vin",
        "vehiculo__cliente__rfc",
        "vehiculo__cliente__nombre_comercial",
    )
    list_filter = ("created_at",)
    autocomplete_fields = ("item", "vehiculo")
    list_select_related = ("item", "vehiculo")
    ordering = ("item_id", "-prima_total")
    readonly_fields = ("created_at", "updated_at")
