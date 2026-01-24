# Aqui se definen los roles y permisos a las diferentes apps del proyecto
# hay 4 roles: Admin, Agente, Operador y Lectura

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Set, Dict

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Q



@dataclass(frozen=True)
class AppPolicy:
    """
    Política de permisos por app.
    actions: conjunto de {"add","change","delete","view"}.
    include_manage: incluye permisos custom codename que empiecen con "manage_".
    """
    actions: Set[str]
    include_manage: bool = False


class Command(BaseCommand):
    help = "Crea/actualiza grupos y permisos base (Admin, Agente, Operador, Lectura) con políticas por app."

    @transaction.atomic
    def handle(self, *args, **options):
        # ------------------------------------------------------------------
        # Definición de roles con políticas por app
        # ------------------------------------------------------------------
        roles: Dict[str, Dict[str, AppPolicy]] = {
            # Admin: TODO en todas las apps + todos los manage_*
            "Admin": {
                "accounts": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "documentos": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "catalogos": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "crm": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "autos": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "tarifas": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "cotizador": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "polizas": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
                "finanzas": AppPolicy(actions={"add", "change", "delete", "view"}, include_manage=True),
            },

            # Agente: opera CRM, Autos, Cotizaciones y Pólizas.
            # - Catálogos: puede ver (y opcionalmente editar si deseas)
            # - Finanzas: solo ver
            # - Tarifas: NO
            "Agente": {
                "accounts": AppPolicy(actions={"view"}),  # ver usuarios (opcional)
                "documentos": AppPolicy(actions={"add", "change", "view"}),  # adjuntar archivos
                "catalogos": AppPolicy(actions={"view"}),  # ver aseguradoras/productos/coberturas
                "crm": AppPolicy(actions={"add", "change", "view"}, include_manage=False),
                "autos": AppPolicy(actions={"add", "change", "view"}),
                "cotizador": AppPolicy(actions={"add", "change", "view"}, include_manage=True),
                "polizas": AppPolicy(actions={"add", "change", "view"}, include_manage=True),
                "finanzas": AppPolicy(actions={"view"}),  # solo consulta
                # "tarifas": (no incluido)
            },

            # Operador: captura y seguimiento.
            # - Catálogos: solo ver
            # - CRM/Autos/Cotizador/Polizas/Docs: add/change/view (sin delete)
            # - Finanzas: no
            # - Tarifas: no
            "Operador": {
                "documentos": AppPolicy(actions={"add", "change", "view"}),
                "catalogos": AppPolicy(actions={"view"}),
                "crm": AppPolicy(actions={"add", "change", "view"}),
                "autos": AppPolicy(actions={"add", "change", "view"}),
                "cotizador": AppPolicy(actions={"add", "change", "view"}),
                "polizas": AppPolicy(actions={"add", "change", "view"}),
                # "finanzas": (no incluido)
                # "tarifas": (no incluido)
            },

            # Lectura: view en todo
            "Lectura": {
                "accounts": AppPolicy(actions={"view"}),
                "documentos": AppPolicy(actions={"view"}),
                "catalogos": AppPolicy(actions={"view"}),
                "crm": AppPolicy(actions={"view"}),
                "autos": AppPolicy(actions={"view"}),
                "tarifas": AppPolicy(actions={"view"}),
                "cotizador": AppPolicy(actions={"view"}),
                "polizas": AppPolicy(actions={"view"}),
                "finanzas": AppPolicy(actions={"view"}),
            },
        }

        # ------------------------------------------------------------------
        # Sincronización
        # ------------------------------------------------------------------
        for role_name, app_policies in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)

            perms = self._collect_permissions(app_policies)
            group.permissions.set(perms)

            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Grupo '{role_name}' {'creado' if created else 'actualizado'} "
                    f"con {perms.count()} permisos."
                )
            )

        self.stdout.write(self.style.SUCCESS("✅ Roles y permisos (por app) sembrados correctamente."))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _collect_permissions(self, app_policies: Dict[str, AppPolicy]):
        """
        Junta permisos por IDs para evitar problemas al combinar QuerySets
        (Cannot combine a unique query with a non-unique query).
        """
        perm_ids = set()

        for app_label, policy in app_policies.items():
            base_qs = Permission.objects.filter(content_type__app_label=app_label)

            std_qs = self._std_permissions_qs(base_qs, policy.actions)
            perm_ids.update(std_qs.values_list("id", flat=True))

            if policy.include_manage:
                manage_qs = base_qs.filter(codename__startswith="manage_")
                perm_ids.update(manage_qs.values_list("id", flat=True))

        return Permission.objects.filter(id__in=perm_ids)


    def _std_permissions_qs(self, qs, actions: Iterable[str]):
        """
        Filtra permisos estándar sin regex para máxima compatibilidad con MySQL.
        """
        actions = set(actions)
        q = Q()

        if "add" in actions:
            q |= Q(codename__startswith="add_")
        if "change" in actions:
            q |= Q(codename__startswith="change_")
        if "delete" in actions:
            q |= Q(codename__startswith="delete_")
        if "view" in actions:
            q |= Q(codename__startswith="view_")

        if q == Q():
            return qs.none()

        return qs.filter(q)
