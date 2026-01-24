# Aqui se definen los roles y permisos a las diferentes apps del proyecto
# hay 4 roles: Admin, Agente, Operador y Lectura
# En esta version no hay permisos  a detalle por app

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction


class Command(BaseCommand):
    help = "Crea/actualiza grupos y permisos base (Admin, Agente, Operador, Lectura)."

    @transaction.atomic
    def handle(self, *args, **options):
        # Apps del proyecto (ajusta si agregas/quitas apps)
        ALL_APPS = {
            "accounts",
            "autos",
            "catalogos",
            "cotizador",
            "crm",
            "documentos",
            "finanzas",
            "polizas",
            "tarifas",
        }

        # ------------------------------------------------------------------
        # Definición de roles
        # ------------------------------------------------------------------
        roles = {
            # Admin: TODO
            "Admin": {
                "apps": ALL_APPS,
                "actions": {"add", "change", "delete", "view"},
                "include_custom_manage_perms": True,
                "exclude_delete": False,
            },

            # Agente: opera clientes y cotizaciones/pólizas, pero no administra reglas/tarifas ni finanzas
            "Agente": {
                "apps": {"catalogos", "crm", "autos", "cotizador", "polizas", "documentos"},
                "actions": {"add", "change", "view"},
                "include_custom_manage_perms": True,   # incluye manage_* de esas apps
                "exclude_delete": True,                # por defecto no elimina
            },

            # Operador: captura/seguimiento (sin borrar), sin tarifas y sin finanzas
            "Operador": {
                "apps": {"catalogos", "crm", "autos", "cotizador", "polizas", "documentos"},
                "actions": {"add", "change", "view"},
                "include_custom_manage_perms": False,  # NO incluye manage_* (más restringido)
                "exclude_delete": True,
            },

            # Lectura: solo ver (útil para supervisión)
            "Lectura": {
                "apps": ALL_APPS,
                "actions": {"view"},
                "include_custom_manage_perms": False,
                "exclude_delete": True,
            },
        }

        # ------------------------------------------------------------------
        # Sincronización
        # ------------------------------------------------------------------
        for role_name, cfg in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)

            perms = self._build_permissions_queryset(
                apps=cfg["apps"],
                actions=cfg["actions"],
                include_custom_manage_perms=cfg["include_custom_manage_perms"],
            )

            if cfg.get("exclude_delete", False):
                perms = perms.exclude(codename__startswith="delete_")

            # Importante: sincronizar (reemplaza permisos del grupo)
            group.permissions.set(perms)

            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Grupo '{role_name}' {'creado' if created else 'actualizado'} "
                    f"con {perms.count()} permisos."
                )
            )

        self.stdout.write(self.style.SUCCESS("✅ Roles y permisos sembrados correctamente."))

    def _build_permissions_queryset(self, apps, actions, include_custom_manage_perms: bool):
        """
        Obtiene los permisos para un conjunto de apps y acciones estándar de Django:
        add_*, change_*, delete_*, view_*.
        También puede incluir permisos custom tipo manage_* definidos en Meta.permissions.
        """
        qs = Permission.objects.filter(content_type__app_label__in=apps)

        # Permisos estándar por acción
        prefixes = []
        if "add" in actions:
            prefixes.append("add_")
        if "change" in actions:
            prefixes.append("change_")
        if "delete" in actions:
            prefixes.append("delete_")
        if "view" in actions:
            prefixes.append("view_")

        std_qs = qs.filter(codename__regex=r"^(" + "|".join(prefixes) + ")") if prefixes else qs.none()

        if include_custom_manage_perms:
            custom_qs = qs.filter(codename__startswith="manage_")
            return (std_qs | custom_qs).distinct()

        return std_qs.distinct()
