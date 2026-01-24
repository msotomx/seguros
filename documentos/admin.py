from django.contrib import admin
from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre_archivo", "tipo", "tamano", "subido_por", "created_at")
    search_fields = ("nombre_archivo", "hash", "subido_por__username", "subido_por__email")
    list_filter = ("tipo", "created_at")
    autocomplete_fields = ("subido_por",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    # Opcional: para evitar cargar todo el archivo en admin y mejorar UX
    readonly_fields = ("tamano", "hash", "created_at", "updated_at")
