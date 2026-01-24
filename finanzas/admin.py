from django.contrib import admin
from .models import Pago, Comision


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "poliza",
        "estatus",
        "monto",
        "metodo",
        "referencia",
        "fecha_programada",
        "fecha_pago",
        "created_at",
    )
    search_fields = (
        "poliza__numero_poliza",
        "poliza__cliente__nombre_comercial",
        "poliza__cliente__nombre",
        "poliza__cliente__rfc",
        "referencia",
        "metodo",
        "comprobante__nombre_archivo",
        "comprobante__hash",
    )
    list_filter = ("estatus", "metodo", "fecha_programada", "fecha_pago", "created_at")
    autocomplete_fields = ("poliza", "comprobante")
    list_select_related = ("poliza",)
    date_hierarchy = "fecha_programada"
    ordering = ("-fecha_programada", "-created_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Póliza", {"fields": ("poliza",)}),
        ("Pago", {"fields": ("estatus", "monto", "metodo", "referencia")}),
        ("Fechas", {"fields": ("fecha_programada", "fecha_pago")}),
        ("Comprobante", {"fields": ("comprobante",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = (
        "poliza",
        "agente",
        "porcentaje",
        "monto",
        "estatus",
        "fecha_pago",
        "created_at",
    )
    search_fields = (
        "poliza__numero_poliza",
        "poliza__cliente__nombre_comercial",
        "poliza__cliente__nombre",
        "poliza__cliente__rfc",
        "agente__username",
        "agente__email",
    )
    list_filter = ("estatus", "agente", "fecha_pago", "created_at")
    autocomplete_fields = ("poliza", "agente")
    list_select_related = ("poliza", "agente")
    date_hierarchy = "fecha_pago"
    ordering = ("-created_at", "-fecha_pago")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Relación", {"fields": ("poliza", "agente")}),
        ("Comisión", {"fields": ("porcentaje", "monto", "estatus")}),
        ("Fecha de pago", {"fields": ("fecha_pago",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )
