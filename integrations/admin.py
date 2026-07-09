from django.contrib import admin
from .models import AseguradoraConfiguracion


@admin.register(AseguradoraConfiguracion)
class AseguradoraConfiguracionAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "ambiente",
        "nombre",
        "activo",
        "updated_at",
    )

    list_filter = (
        "provider",
        "ambiente",
        "activo",
    )

    search_fields = (
        "nombre",
        "provider",
    )
