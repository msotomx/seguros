# ui/services/perms.py 
from finanzas.models import Pago


def user_is_supervisor(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=["Supervisor", "Admin"]).exists()

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

# Regla para Aplicar y subir comprobantes de pago:
# Cliente: unicamente puede ver sus pagos desde el portal
# por cliente__user_portal=user
#
# Agente
# Debe poder:
# - ver pagos de pólizas donde poliza.agente == request.user
# - subir comprobantes de los pagos de sus clientes
# - ver comprobantes de esos pagos
#
# Supervisor/Admin
# Debe poder:
# - ver todos los pagos
# - subir/ver comprobantes de cualquier pago


def can_manage_pago(user, pago):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if user.groups.filter(name__in=["Supervisor", "Admin"]).exists():
        return True

    if pago.poliza and pago.poliza.agente_id == user.id:
        return True

    return False

# Para capturar pagos de una poliza
def can_manage_pago2(user, pago: Pago) -> bool:
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

def pagos_visibles_para_usuario(user, queryset=None):
    from finanzas.models import Pago

    qs = queryset or Pago.objects.all()

    if not user.is_authenticated:
        return qs.none()

    if user.is_superuser or user_is_supervisor(user):
        return qs

    return qs.filter(poliza__agente=user)




def can_view_pago_comprobante(user, pago):
    if not user.is_authenticated:
        return False

    # Cliente portal: solo lo suyo
    cliente = getattr(pago, "cliente", None)
    if cliente and cliente.user_portal_id == user.id and cliente.portal_activo:
        return True

    # Agente/supervisor/backoffice
    return can_manage_pago(user, pago)
