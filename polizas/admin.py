from django.contrib import admin
from .models import Poliza, Endoso, Renovacion, Incidente, Siniestro


@admin.register(Poliza)
class PolizaAdmin(admin.ModelAdmin):
    list_display = (
        "numero_poliza",
        "cliente",
        "aseguradora",
        "producto",
        "estatus",
        "vigencia_desde",
        "vigencia_hasta",
        "prima_total",
        "forma_pago",
        "agente",
        "created_at",
    )
    search_fields = (
        "numero_poliza",
        "cliente__nombre_comercial",
        "cliente__nombre",
        "cliente__apellido_paterno",
        "cliente__rfc",
        "aseguradora__nombre",
        "producto__nombre_producto",
        "vehiculo__placas",
        "vehiculo__vin",
        "agente__username",
        "agente__email",
    )
    list_filter = ("estatus", "aseguradora", "producto", "vigencia_hasta", "created_at")
    autocomplete_fields = (
        "cliente",
        "vehiculo",
        "flotilla",
        "aseguradora",
        "producto",
        "cotizacion_item",
        "agente",
        "documento",
    )
    list_select_related = ("cliente", "aseguradora", "producto", "vehiculo", "flotilla", "agente")
    date_hierarchy = "vigencia_hasta"
    ordering = ("-vigencia_hasta", "-created_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Asegurado", {"fields": ("cliente", "vehiculo", "flotilla")}),
        ("Producto", {"fields": ("aseguradora", "producto", "cotizacion_item")}),
        ("Vigencia / estatus", {"fields": ("numero_poliza", "vigencia_desde", "vigencia_hasta", "estatus")}),
        ("Prima", {"fields": ("prima_total", "forma_pago")}),
        ("Gestión", {"fields": ("agente", "documento")}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Endoso)
class EndosoAdmin(admin.ModelAdmin):
    list_display = ("poliza", "tipo_endoso", "fecha", "prima_ajuste", "created_at")
    search_fields = (
        "poliza__numero_poliza",
        "poliza__cliente__nombre_comercial",
        "poliza__cliente__nombre",
        "poliza__cliente__rfc",
        "descripcion",
    )
    list_filter = ("tipo_endoso", "fecha", "created_at")
    autocomplete_fields = ("poliza", "documento")
    list_select_related = ("poliza",)
    date_hierarchy = "fecha"
    ordering = ("-fecha", "-created_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Encabezado", {"fields": ("poliza", "tipo_endoso", "fecha")}),
        ("Detalle", {"fields": ("descripcion",)}),
        ("Ajuste", {"fields": ("prima_ajuste",)}),
        ("Documento", {"fields": ("documento",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Renovacion)
class RenovacionAdmin(admin.ModelAdmin):
    list_display = ("poliza_anterior", "poliza_nueva", "fecha_renovacion", "resultado", "created_at")
    search_fields = (
        "poliza_anterior__numero_poliza",
        "poliza_nueva__numero_poliza",
        "resultado",
    )
    list_filter = ("fecha_renovacion", "created_at", "resultado")
    autocomplete_fields = ("poliza_anterior", "poliza_nueva")
    list_select_related = ("poliza_anterior", "poliza_nueva")
    date_hierarchy = "fecha_renovacion"
    ordering = ("-fecha_renovacion", "-created_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Incidente)
class IncidenteAdmin(admin.ModelAdmin):
    list_display = ("cliente", "vehiculo", "conductor", "tipo_incidente", "fecha_incidente", "estatus", "created_at")
    search_fields = (
        "cliente__nombre_comercial",
        "cliente__nombre",
        "cliente__rfc",
        "vehiculo__placas",
        "vehiculo__vin",
        "conductor__nombre",
        "descripcion",
        "resolucion",
    )
    list_filter = ("tipo_incidente", "estatus", "fecha_incidente", "created_at")
    autocomplete_fields = ("cliente", "vehiculo", "conductor", "documento")
    list_select_related = ("cliente", "vehiculo", "conductor")
    date_hierarchy = "fecha_incidente"
    ordering = ("-fecha_incidente", "-created_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Encabezado", {"fields": ("cliente", "vehiculo", "conductor")}),
        ("Incidente", {"fields": ("tipo_incidente", "fecha_incidente", "estatus")}),
        ("Detalle", {"fields": ("descripcion", "monto_estimado", "resolucion")}),
        ("Documento", {"fields": ("documento",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Siniestro)
class SiniestroAdmin(admin.ModelAdmin):
    list_display = (
        "numero_siniestro",
        "aseguradora",
        "incidente",
        "estatus",
        "fecha_reporte",
        "fecha_cierre",
        "monto_reclamado",
        "monto_pagado",
        "created_at",
    )
    search_fields = (
        "numero_siniestro",
        "aseguradora__nombre",
        "incidente__cliente__nombre_comercial",
        "incidente__cliente__nombre",
        "incidente__cliente__rfc",
        "notas",
    )
    list_filter = ("aseguradora", "estatus", "fecha_reporte", "fecha_cierre", "created_at")
    autocomplete_fields = ("incidente", "aseguradora", "documento")
    list_select_related = ("aseguradora", "incidente")
    date_hierarchy = "fecha_reporte"
    ordering = ("-fecha_reporte", "-created_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Encabezado", {"fields": ("aseguradora", "numero_siniestro", "estatus")}),
        ("Fechas", {"fields": ("fecha_reporte", "fecha_cierre")}),
        ("Relacionado", {"fields": ("incidente",)}),
        ("Montos", {"fields": ("monto_reclamado", "monto_pagado")}),
        ("Notas / Documento", {"fields": ("notas", "documento")}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )
