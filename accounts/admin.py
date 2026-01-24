from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rol", "activo", "created_at")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    list_filter = ("rol", "activo")
    autocomplete_fields = ("user", "aseguradoras_permitidas")
    ordering = ("user__username",)
