# ui/services/perms.py 
from finanzas.models import Pago

def can_manage_poliza(user, poliza):
    if user.is_superuser:
        return True
    if user.has_perm("polizas.manage_polizas"):
        return True
    # Supervisor/Admin por grupo (ajusta si tus nombres son distintos)
    if user.groups.filter(name__in=["Supervisor", "Admin"]).exists():
        return True
    if user.groups.filter(name="Agente").exists():
        return poliza.agente_id == user.id
    return False

# Para capturar pagos de una poliza
def can_manage_pago(user, pago: Pago) -> bool:
    # Admin/Supervisor/permiso global
    if user.groups.filter(name__in=["Supervisor", "Admin"]).exists():
        return True
    # Agente: solo pagos de sus pólizas
    return pago.poliza.agente_id == user.id


# Helper para todos, poliza_list este no se usa para un pago en especifico
def can_see_pagos(user) -> bool:
    if user.is_superuser:
        return True
    if user.has_perm("finanzas.manage_pagos"):
        return True
    if user.groups.filter(name__in=["Supervisor", "Admin"]).exists():
        return True
    return False #False debe ser False

# Helper para todos, comision_list este no se usa para un pago en especifico
def can_see_comisiones(user) -> bool:
    if user.is_superuser:
        return True
    if user.has_perm("finanzas.manage_comisiones"):
        return True
    if user.groups.filter(name__in=["Supervisor", "Admin"]).exists():
        return True
    return False

def can_admin_polizas(user) -> bool:
    return (
        user.is_superuser
        or user.has_perm("polizas.manage_polizas")
        or user.groups.filter(name__in=["Admin", "Supervisor"]).exists()
    )

def can_update_poliza_numero(user, poliza) -> bool:
    # Admin/Supervisor siempre
    if user.is_superuser or user.groups.filter(name__in=["Admin", "Supervisor"]).exists():
        return True
    # Agente: solo su póliza y solo si está en proceso
    return poliza.agente_id == user.id and poliza.estatus == poliza.Estatus.EN_PROCESO

def can_download_documento(user, documento):
    if user.groups.filter(name__in=["Admin", "Supervisor"]).exists():
        return True

    # Si es agente, solo documentos de sus pólizas
    return documento.poliza.agente_id == user.id
