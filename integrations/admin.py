from django.contrib import admin

from integrations.models import (
    AseguradoraConfiguracion,
    ProviderSetting,
)

# Inline de ProviderSetting
class ProviderSettingInline(admin.TabularInline):
    model = ProviderSetting
    extra = 1

    fields = (
        "key",
        "value",
        "value_type",
        "activo",
    )

    ordering = (
        "key",
    )

    show_change_link = True

@admin.register(AseguradoraConfiguracion)
class AseguradoraConfiguracionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "provider",
        "aseguradora",
        "ambiente",
        "ramo",
        "activo",
        "prioridad",
        "supports_quote",
    )

    list_filter = (
        "provider",
        "ambiente",
        "ramo",
        "activo",
        "supports_quote",
        "supports_issue",
        "supports_documents",
    )

    search_fields = (
        "nombre",
        "provider",
        "aseguradora__nombre",
        "token_url",
        "base_url",
        "grouping_id",
        "rate_id",
        "business_profile_name",
    )

    ordering = (
        "prioridad",
        "provider",
        "ambiente",
    )

    readonly_fields = (
        "id",
    )

    inlines = (
        ProviderSettingInline,
    )

    fieldsets = (
        (
            "Identificación",
            {
                "fields": (
                    "id",
                    "aseguradora",
                    "nombre",
                    "provider",
                    "ambiente",
                    "ramo",
                    "activo",
                    "prioridad",
                )
            },
        ),
        (
            "Conectividad",
            {
                "fields": (
                    "token_url",
                    "base_url",
                    "client_id",
                    "client_secret",
                    "resource_id",
                    "api_version",
                    "timeout",
                    "grouping_id",
                    "rate_id",
                    "business_profile_name",
                )
            },
        ),
        (
            "Capacidades",
            {
                "fields": (
                    "supports_quote",
                    "supports_issue",
                    "supports_documents",
                    "supports_payments",
                    "supports_endorsements",
                    "supports_cancellation",
                    "supports_renewal",
                )
            },
        ),
    )


@admin.register(ProviderSetting)
class ProviderSettingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "configuracion",
        "key",
        "value_type",
        "masked_value",
        "activo",
    )

    list_filter = (
        "activo",
        "value_type",
        "configuracion__provider",
        "configuracion__ambiente",
        "configuracion__ramo",
    )

    search_fields = (
        "key",
        "value",
        "configuracion__nombre",
        "configuracion__provider",
    )

    ordering = (
        "configuracion",
        "key",
    )

    autocomplete_fields = (
        "configuracion",
    )

    readonly_fields = (
        "id",
    )

    @admin.display(
        description="Valor",
    )
    def masked_value(self, obj):
        secret_keys = {
            "APP_KEY",
            "CLIENT_SECRET",
            "PASSWORD",
            "SECRET",
            "TOKEN",
            "ACCESS_TOKEN",
        }

        normalized_key = obj.key.upper()

        is_secret = any(
            secret_key in normalized_key
            for secret_key in secret_keys
        )

        if is_secret:
            return "********"

        value = str(obj.value or "")

        if len(value) > 60:
            return f"{value[:57]}..."

        return value
    
from django.contrib import admin

from .models import Catalog, CatalogItem


class CatalogItemInline(admin.TabularInline):
    model = CatalogItem
    extra = 1
    fields = (
        "code",
        "name",
        "sort_order",
        "is_active",
    )
    ordering = (
        "sort_order",
        "name",
    )


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_active",
    )
    list_filter = (
        "is_active",
    )
    search_fields = (
        "code",
        "name",
    )
    inlines = [
        CatalogItemInline,
    ]


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "catalog",
        "sort_order",
        "is_active",
    )
    list_filter = (
        "catalog",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "catalog__code",
        "catalog__name",
    )
    ordering = (
        "catalog",
        "sort_order",
        "name",
    )

from .models import ProviderCatalogMapping

@admin.register(ProviderCatalogMapping)
class ProviderCatalogMappingAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "catalog",
        "catalog_item",
        "external_code",
        "external_name",
        "is_active",
    )

    list_filter = (
        "provider",
        "catalog",
        "is_active",
    )

    search_fields = (
        "provider__aseguradora__nombre",
        "catalog__code",
        "catalog__name",
        "catalog_item__code",
        "catalog_item__name",
        "external_code",
        "external_name",
    )

    autocomplete_fields = (
        "provider",
        "catalog",
        "catalog_item",
    )

    ordering = (
        "provider",
        "catalog",
        "catalog_item__sort_order",
        "catalog_item__name",
    )
