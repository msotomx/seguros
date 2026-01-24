from django.conf import settings
from django.db import models
from core.models import TimeStampedModel


# ---------------------------------------------------------------------
# Seguridad / Usuarios (Permisos por usuario)
# ---------------------------------------------------------------------
# Nota: Django ya trae permisos por modelo (add/change/delete/view) y grupos.
# Aquí agregamos un perfil y algunas banderas opcionales, además de permisos custom.

class UserProfile(TimeStampedModel):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        AGENTE = "AGENTE", "Agente"
        OPERADOR = "OPERADOR", "Operador"
        LECTURA = "LECTURA", "Solo lectura"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.AGENTE, db_index=True)
    telefono = models.CharField(max_length=30, blank=True, default="")
    notas = models.TextField(blank=True, default="")
    activo = models.BooleanField(default=True, db_index=True)

    # Alcance opcional (si quieres restringir qué aseguradoras ve un usuario)
    aseguradoras_permitidas = models.ManyToManyField(
        "catalogos.Aseguradora", blank=True, related_name="usuarios_permitidos"
    )

    class Meta:
        permissions = [
            # permisos “de negocio” (además de add/change/delete/view)
            ("can_quote", "Puede cotizar"),
            ("can_issue_policy", "Puede emitir póliza"),
            ("can_cancel_policy", "Puede cancelar póliza"),
            ("can_manage_tariffs", "Puede administrar tarifas y reglas"),
            ("can_view_finance", "Puede ver finanzas (pagos/comisiones)"),
            ("can_manage_finance", "Puede administrar finanzas (pagos/comisiones)"),
        ]
