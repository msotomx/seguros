import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from crm.models import Cliente

User = get_user_model()


def generar_password_temporal(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@transaction.atomic
def crear_acceso_portal_cliente(cliente: Cliente):
    """
    Convierte un Cliente en usuario del portal.

    - Si ya tiene user_portal, solo activa portal_activo.
    - Si no tiene, crea User.
    - Asigna grupo Portal.
    - Relaciona Cliente.user_portal.
    - Regresa user y password temporal.
    """

    if cliente.user_portal:
        cliente.portal_activo = True
        cliente.save(update_fields=["portal_activo"])

        return {
            "user": cliente.user_portal,
            "password_temporal": None,
            "created": False,
        }

    email = (cliente.email_principal or "").strip().lower()

    if not email:
        raise ValueError("El cliente no tiene email principal para crear acceso al portal.")

    username_base = email
    username = username_base
    counter = 1

    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{username_base}-{counter}"

    telefono = (cliente.telefono_principal or "").strip()
    if telefono:
        password_temporal = telefono
    else:
        password_temporal = generar_password_temporal()

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password_temporal,
        first_name=getattr(cliente, "nombre", "") or "",
        last_name=getattr(cliente, "apellido_paterno", "") or "",
        is_active=True,
    )

    grupo_portal, _ = Group.objects.get_or_create(name="Portal")
    user.groups.add(grupo_portal)

    cliente.user_portal = user
    cliente.portal_activo = True
    cliente.save(update_fields=["user_portal", "portal_activo"])

    return {
        "user": user,
        "password_temporal": password_temporal,
        "created": True,
    }
