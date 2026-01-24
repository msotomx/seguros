from django.contrib import admin
from .models import (
    Aseguradora,
    AseguradoraContacto,
    ProductoSeguro,
    CoberturaCatalogo,
    ProductoCobertura,
)


@admin.register(Aseguradora)
class AseguradoraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rfc", "telefono_contacto", "email_contacto", "is_active", "created_at")
    search_fields = ("nombre", "rfc", "telefono_contacto", "email_contacto")
    list_filter = ("is_active",)
    ordering = ("nombre",)


@admin.register(AseguradoraContacto)
class AseguradoraContactoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "aseguradora", "puesto", "telefono", "email", "is_active", "created_at")
    search_fields = ("nombre", "puesto", "telefono", "email", "aseguradora__nombre")
    list_filter = ("is_active", "aseguradora")
    autocomplete_fields = ("aseguradora",)
    list_select_related = ("aseguradora",)
    ordering = ("aseguradora__nombre", "nombre")


@admin.register(ProductoSeguro)
class ProductoSeguroAdmin(admin.ModelAdmin):
    list_display = ("nombre_producto", "aseguradora", "tipo_producto", "modelo_calculo", "moneda", "is_active", "created_at")
    search_fields = ("nombre_producto", "aseguradora__nombre")
    list_filter = ("is_active", "tipo_producto", "modelo_calculo", "aseguradora", "moneda")
    autocomplete_fields = ("aseguradora",)
    list_select_related = ("aseguradora",)
    ordering = ("aseguradora__nombre", "nombre_producto")


@admin.register(CoberturaCatalogo)
class CoberturaCatalogoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo_valor", "is_active", "created_at")
    search_fields = ("codigo", "nombre")
    list_filter = ("is_active", "tipo_valor")
    ordering = ("codigo",)


@admin.register(ProductoCobertura)
class ProductoCoberturaAdmin(admin.ModelAdmin):
    list_display = ("producto", "cobertura", "incluida", "valor_default", "created_at")
    search_fields = ("producto__nombre_producto", "producto__aseguradora__nombre", "cobertura__codigo", "cobertura__nombre")
    list_filter = ("incluida", "producto__aseguradora", "producto__tipo_producto")
    autocomplete_fields = ("producto", "cobertura")
    list_select_related = ("producto", "cobertura")
    ordering = ("producto__aseguradora__nombre", "producto__nombre_producto", "cobertura__codigo")
