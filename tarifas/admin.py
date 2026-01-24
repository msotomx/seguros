from django.contrib import admin
from .models import (
    ZonaTarifa,
    ZonaTarifaDetalle,
    VariableTarifa,
    TablaFactor,
    TablaFactorRango,
    ReglaTarifa,
    ReglaCondicion,
    ReglaAccion,
    CoberturaTarifa,
    DeducibleOpcion,
)


@admin.register(ZonaTarifa)
class ZonaTarifaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "is_active", "created_at")
    search_fields = ("codigo", "nombre", "descripcion")
    list_filter = ("is_active", "created_at")
    ordering = ("codigo",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ZonaTarifaDetalle)
class ZonaTarifaDetalleAdmin(admin.ModelAdmin):
    list_display = ("zona", "pais", "estado", "ciudad", "cp_inicio", "cp_fin", "created_at")
    search_fields = ("zona__codigo", "zona__nombre", "pais", "estado", "ciudad", "cp_inicio", "cp_fin")
    list_filter = ("pais", "estado", "zona", "created_at")
    autocomplete_fields = ("zona",)
    list_select_related = ("zona",)
    ordering = ("zona__codigo", "pais", "estado", "ciudad", "cp_inicio", "cp_fin")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VariableTarifa)
class VariableTarifaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "origen", "tipo_dato", "is_active", "created_at")
    search_fields = ("codigo", "nombre", "descripcion")
    list_filter = ("origen", "tipo_dato", "is_active", "created_at")
    ordering = ("codigo",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TablaFactor)
class TablaFactorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "is_active", "created_at")
    search_fields = ("nombre", "descripcion")
    list_filter = ("tipo", "is_active", "created_at")
    ordering = ("nombre",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TablaFactorRango)
class TablaFactorRangoAdmin(admin.ModelAdmin):
    list_display = (
        "tabla",
        "var1",
        "var1_min",
        "var1_max",
        "var2",
        "var2_min",
        "var2_max",
        "valor",
        "prioridad",
        "is_active",
        "created_at",
    )
    search_fields = (
        "tabla__nombre",
        "var1__codigo",
        "var1__nombre",
        "var2__codigo",
        "var2__nombre",
    )
    list_filter = ("tabla", "is_active", "created_at")
    autocomplete_fields = ("tabla", "var1", "var2")
    list_select_related = ("tabla", "var1", "var2")
    ordering = ("tabla__nombre", "-prioridad", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReglaTarifa)
class ReglaTarifaAdmin(admin.ModelAdmin):
    list_display = ("producto", "nombre", "tipo_regla", "modo_aplicacion", "prioridad", "is_active", "created_at")
    search_fields = ("nombre", "producto__nombre_producto", "producto__aseguradora__nombre")
    list_filter = ("tipo_regla", "modo_aplicacion", "is_active", "producto__aseguradora", "created_at")
    autocomplete_fields = ("producto",)
    list_select_related = ("producto",)
    ordering = ("producto__aseguradora__nombre", "producto__nombre_producto", "tipo_regla", "-prioridad")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReglaCondicion)
class ReglaCondicionAdmin(admin.ModelAdmin):
    list_display = ("regla", "grupo", "orden", "variable", "operador", "negada", "valor1", "valor2", "created_at")
    search_fields = (
        "regla__nombre",
        "regla__producto__nombre_producto",
        "variable__codigo",
        "variable__nombre",
        "valor1",
        "valor2",
    )
    list_filter = ("operador", "negada", "created_at", "regla__producto__aseguradora")
    autocomplete_fields = ("regla", "variable")
    list_select_related = ("regla", "variable")
    ordering = ("regla_id", "grupo", "orden")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReglaAccion)
class ReglaAccionAdmin(admin.ModelAdmin):
    list_display = (
        "regla",
        "orden",
        "tipo_accion",
        "variable_destino",
        "valor",
        "valor_texto",
        "tabla_factor",
        "redondeo",
        "minimo",
        "maximo",
        "created_at",
    )
    search_fields = (
        "regla__nombre",
        "regla__producto__nombre_producto",
        "variable_destino",
        "valor_texto",
    )
    list_filter = ("tipo_accion", "redondeo", "created_at", "regla__producto__aseguradora")
    autocomplete_fields = ("regla", "tabla_factor")
    list_select_related = ("regla", "tabla_factor")
    ordering = ("regla_id", "orden")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CoberturaTarifa)
class CoberturaTarifaAdmin(admin.ModelAdmin):
    list_display = (
        "producto",
        "cobertura",
        "modo_costo",
        "monto_fijo",
        "porcentaje",
        "tabla_factor",
        "minimo",
        "maximo",
        "is_active",
        "created_at",
    )
    search_fields = (
        "producto__nombre_producto",
        "producto__aseguradora__nombre",
        "cobertura__codigo",
        "cobertura__nombre",
        "tabla_factor__nombre",
    )
    list_filter = ("modo_costo", "is_active", "producto__aseguradora", "created_at")
    autocomplete_fields = ("producto", "cobertura", "tabla_factor")
    list_select_related = ("producto", "cobertura", "tabla_factor")
    ordering = ("producto__aseguradora__nombre", "producto__nombre_producto", "cobertura__codigo")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DeducibleOpcion)
class DeducibleOpcionAdmin(admin.ModelAdmin):
    list_display = ("producto", "tipo", "valor", "es_porcentaje", "afecta_prima", "factor_prima", "is_active", "created_at")
    search_fields = ("producto__nombre_producto", "producto__aseguradora__nombre")
    list_filter = ("tipo", "es_porcentaje", "afecta_prima", "is_active", "producto__aseguradora", "created_at")
    autocomplete_fields = ("producto",)
    list_select_related = ("producto",)
    ordering = ("producto__aseguradora__nombre", "producto__nombre_producto", "tipo")
    readonly_fields = ("created_at", "updated_at")
