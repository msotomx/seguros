from django.contrib import admin
from .models import Pago, Comision
from .models import Pago, PagoTransaccion

class PagoTransaccionInline(admin.TabularInline):
    model = PagoTransaccion
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        "created_at",
        "tipo",
        "provider",
        "provider_payment_id",
        "provider_preference_id",
        "provider_status",
        "monto",
        "moneda",
        "procesado",
    )
    readonly_fields = fields


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "poliza",
        "cliente",
        "concepto",
        "monto",
        "monto_pagado",
        "estatus",
        "provider",
        "provider_status",
        "metodo",
        "referencia",
        "fecha_programada",
        "fecha_vencimiento",
        "fecha_pago",
    )

    list_filter = (
        "estatus",
        "provider",
        "provider_status",
        "metodo",
        "fecha_programada",
        "fecha_vencimiento",
        "fecha_pago",
    )

    search_fields = (
        "id",
        "concepto",
        "descripcion",
        "referencia",
        "provider_payment_id",
        "provider_preference_id",
        "poliza__numero_poliza",
        "cliente__nombre",
        "cliente__apellido_paterno",
        "cliente__apellido_materno",
        "cliente__nombre_comercial",
        "cliente__email_principal",
        "cliente__telefono_principal",
        "cliente__rfc",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "monto_pendiente",
        "esta_vencido",
        "webhook_last_payload",
        "payload_resumen_json",
    )

    inlines = [PagoTransaccionInline]

    fieldsets = (
        ("Relaciones", {
            "fields": (
                "poliza",
                "cliente",
                "usuario_portal",
                "comprobante",
            )
        }),
        ("Información del pago", {
            "fields": (
                "concepto",
                "descripcion",
                "monto",
                "monto_pagado",
                "moneda",
                "comision_provider",
                "estatus",
                "metodo",
                "referencia",
            )
        }),
        ("Fechas", {
            "fields": (
                "fecha_programada",
                "fecha_vencimiento",
                "fecha_pago",
                "fecha_pago_provider",
            )
        }),        
        ("Provider", {
            "fields": (
                "provider",
                "provider_payment_id",
                "provider_preference_id",
                "provider_status",
                "checkout_url",
            )
        }),
        ("Diagnóstico", {
            "fields": (
                "monto_pendiente",
                "esta_vencido",
                "webhook_last_payload",
                "payload_resumen_json",
                "observaciones",
            )
        }),
        ("Auditoría", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    autocomplete_fields = ("poliza", "cliente", "usuario_portal", "comprobante")


@admin.register(PagoTransaccion)
class PagoTransaccionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pago",
        "tipo",
        "provider",
        "provider_payment_id",
        "provider_preference_id",
        "provider_status",
        "monto",
        "moneda",
        "procesado",
        "created_at",
    )

    list_filter = (
        "tipo",
        "provider",
        "provider_status",
        "procesado",
        "created_at",
    )

    search_fields = (
        "id",
        "pago__id",
        "provider_payment_id",
        "provider_preference_id",
        "provider_status",
        "observaciones",
        "error_message",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "payload",
    )

    autocomplete_fields = ("pago",)

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
