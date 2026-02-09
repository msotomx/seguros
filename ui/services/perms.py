# ui/services/perms.py 
def can_manage_poliza(user, poliza):
    if user.has_perm("polizas.manage_polizas"):
        return True
    if user.groups.filter(name="Agente").exists():
        return poliza.agente_id == user.id
    return False


def can_manage_pagos(user) -> bool:
    if user.is_superuser:
        return True
    if user.has_perm("finanzas.manage_pagos"):
        return True
    # Supervisores/admins por grupo (ajusta nombres reales)
    if user.groups.filter(name__in=["Supervisor", "Admin"]).exists():
        return True
    return False
