from django.utils.timezone import localdate
from datetime import timedelta
from django.conf import settings

from finanzas.models import Pago
from finanzas.services.recordatorios import registrar_recordatorio_pago
from finanzas.services.recordatorios_whatsapp import enviar_recordatorio_whatsapp


DIAS_POR_VENCER = [7, 3, 1]
DIAS_VENCIDO = [1, 3, 7]


def _procesar_recordatorio(*, pago, categoria, dias, dry_run=False):
    if dry_run:
        return {"ok": True, "modo": "dry-run"}

    whatsapp_enabled = bool(getattr(settings, "WHATSAPP_ENABLED", False))

    if whatsapp_enabled:
        return enviar_recordatorio_whatsapp(
            pago=pago,
            actor=None,
            categoria=categoria,
            dias=dias,
        )

    registrar_recordatorio_pago(
        pago=pago,
        actor=None,
        canal="AUTOMATICO",
        categoria=categoria,
        dias=dias,
        usar_dedupe=True,
    )
    return {"ok": True, "modo": "solo-evento"}


def generar_recordatorios_automaticos(*, dry_run=False):
    hoy = localdate()
    generados = 0
    detalle = {
        "por_vencer": {7: 0, 3: 0, 1: 0},
        "vencido": {1: 0, 3: 0, 7: 0},
        "errores": [],
    }

    # Por vencer
    for dias in DIAS_POR_VENCER:
        fecha_objetivo = hoy + timedelta(days=dias)

        pagos = (
            Pago.objects
            .select_related("poliza", "cliente")
            .filter(
                estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.PARCIAL],
                fecha_vencimiento=fecha_objetivo,
            )
            .exclude(poliza__estatus="CANCELADA")
        )

        for pago in pagos:
            result = _procesar_recordatorio(
                pago=pago,
                categoria="POR_VENCER",
                dias=dias,
                dry_run=dry_run,
            )

            if result.get("ok"):
                generados += 1
                detalle["por_vencer"][dias] += 1
            else:
                detalle["errores"].append({
                    "pago_id": pago.id,
                    "categoria": "POR_VENCER",
                    "dias": dias,
                    "error": result.get("error") or result.get("data"),
                })

    # Vencidos
    for dias in DIAS_VENCIDO:
        fecha_objetivo = hoy - timedelta(days=dias)

        pagos = (
            Pago.objects
            .select_related("poliza", "cliente")
            .filter(
                estatus=Pago.Estatus.VENCIDO,
                fecha_vencimiento=fecha_objetivo,
            )
            .exclude(poliza__estatus="CANCELADA")
        )

        for pago in pagos:
            result = _procesar_recordatorio(
                pago=pago,
                categoria="VENCIDO",
                dias=dias,
                dry_run=dry_run,
            )

            if result.get("ok"):
                generados += 1
                detalle["vencido"][dias] += 1
            else:
                detalle["errores"].append({
                    "pago_id": pago.id,
                    "categoria": "VENCIDO",
                    "dias": dias,
                    "error": result.get("error") or result.get("data"),
                })

    return generados, detalle
