from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from finanzas.models import Comision
from polizas.services import log_poliza_event


porcentaje_comision = Decimal(str(settings.COMISION_PORCENTAJE_DEFAULT))

@transaction.atomic
def marcar_comision_pagada(*, comision, usuario=None, notas=""):
    if comision.estatus == comision.Estatus.PAGADA:
        return comision

    comision.estatus = comision.Estatus.PAGADA
    comision.fecha_pago = timezone.localdate()

    if notas:
        comision.notas = notas

    comision.save(update_fields=["estatus", "fecha_pago", "notas", "updated_at"])

    log_poliza_event(
        poliza=comision.poliza,
        tipo="COMISION_PAGADA",
        titulo="Comisión pagada",
        detalle=f"Se marcó como pagada la comisión de {comision.monto_comision}.",
        data={
            "comision_id": comision.id,
            "monto_comision": str(comision.monto_comision),
            "fecha_pago": comision.fecha_pago.isoformat() if comision.fecha_pago else None,
            "notas": comision.notas,
        },
        actor=usuario,
        dedupe_key=f"COMISION_PAGADA:{comision.id}",
    )

    return comision


from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction

from finanzas.models import Comision
from polizas.services import log_poliza_event

def redondear_monto(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def obtener_base_comision(poliza):
    """
    Fase 1:
    La comisión se calcula sobre prima_neta.
    """
    if getattr(poliza, "prima_neta", None) is not None:
        return redondear_monto(poliza.prima_neta)

    return Decimal("0.00")


def resolver_porcentaje_comision(poliza, agente=None):
    """
    Fase 1:
    Usa porcentaje global definido en settings.

    Fase 2:
    Aquí podrá consultarse ConfiguracionComision por aseguradora/producto/ramo
    y después overrides por agente.
    """
    return redondear_monto(getattr(settings, "COMISION_PORCENTAJE_DEFAULT", Decimal("10.00")))


@transaction.atomic
def generar_comision_poliza(*, poliza, agente, usuario=None):
    """
    Genera una comisión para la póliza si no existe previamente
    para la combinación póliza-agente.
    """

    if not agente:
        return None

    existente = Comision.objects.filter(poliza=poliza, agente=agente).first()
    if existente:
        return existente

    porcentaje = resolver_porcentaje_comision(poliza, agente=agente)
    base_calculo = obtener_base_comision(poliza)
    
    if base_calculo <= 0:
        return None

    monto_comision = redondear_monto(base_calculo * (porcentaje / Decimal("100")))
    comision = Comision.objects.create(
        poliza=poliza,
        agente=agente,
        porcentaje=porcentaje,
        base_calculo=base_calculo,
        monto_comision=monto_comision,
        estatus=Comision.Estatus.PENDIENTE,
    )

    log_poliza_event(
        poliza=poliza,
        tipo="COMISION_GENERADA",
        titulo="Comisión generada",
        detalle=f"Se generó comisión de {monto_comision} para {agente}.",
        data={
            "comision_id": comision.id,
            "agente_id": agente.id,
            "agente": str(agente),
            "porcentaje": str(comision.porcentaje),
            "base_calculo": str(comision.base_calculo),
            "base_origen": "prima_neta",
            "monto_comision": str(comision.monto_comision),
            "poliza_id": poliza.id,
        },
        actor=usuario,
        dedupe_key=f"COMISION_GENERADA:{poliza.id}:{agente.id}",
    )

    return comision
