from __future__ import annotations
from django.utils import timezone
from typing import Any, Optional, Dict
from django.db import transaction, IntegrityError
from polizas.models import PolizaEvento, Poliza, Endoso
from decimal import Decimal


def generar_numero_poliza(aseguradora_id: int) -> str:
    # Provisional, pero suficientemente único por aseguradora:
    # POL-<aseg>-<YYYYMMDDHHMMSS>-<ms>
    now = timezone.now()
    return f"POL-{aseguradora_id}-{now:%Y%m%d%H%M%S}-{now.microsecond//1000:03d}"


def log_poliza_event(
    *,
    poliza: Poliza,
    tipo: str,
    actor=None,
    titulo: str = "",
    detalle: str = "",
    data: Optional[Dict[str, Any]] = None,
    dedupe_key: Optional[str] = None,
) -> Optional[PolizaEvento]:
    """
    Crea PolizaEvento con dedupe_key segura.

    - Si dedupe_key choca por UniqueConstraint, regresa None (idempotente).
    - No deja la transacción "rota" aunque estés dentro de un atomic mayor.
    """
    payload = dict(data or {})

    try:
        # Savepoint seguro si ya estás dentro de otra transacción.
        with transaction.atomic():
            evt = PolizaEvento.objects.create(
                poliza=poliza,
                tipo=tipo,
                titulo=titulo,
                detalle=detalle,
                data=payload or None,
                actor=actor,
                dedupe_key=dedupe_key,
            )
            return evt

    except IntegrityError:
        # Duplicate por uq(poliza,tipo,dedupe_key) => ya existe, no crear otro
        return None


# =======================
# ENDOSOS
# =======================

@transaction.atomic
def crear_endoso(
    *,
    poliza,
    tipo_endoso,
    descripcion="",
    prima_ajuste=0,
    fecha=None,
    documento=None,
    usuario=None,
):
    """
    Crea un endoso y registra su evento en bitácora.

    Parámetros:
    - poliza: instancia de Poliza
    - tipo_endoso: valor de Endoso.Tipo
    - descripcion: texto libre
    - prima_ajuste: decimal positivo, negativo o cero
    - fecha: fecha del endoso; si no se envía, usa la fecha actual
    - documento: instancia opcional de Documento
    - usuario: opcional, por si después quieres guardar auditoría adicional
    """

    if fecha is None:
        fecha = timezone.localdate()

    if prima_ajuste in (None, ""):
        prima_ajuste = Decimal("0.00")
    else:
        prima_ajuste = Decimal(str(prima_ajuste))

    endoso = Endoso.objects.create(
        poliza=poliza,
        tipo_endoso=tipo_endoso,
        descripcion=descripcion or "",
        prima_ajuste=prima_ajuste,
        fecha=fecha,
        documento=documento,
    )

    # Aquí después puedes meter lógica específica por tipo de endoso:
    # - cambio de vehículo
    # - cambio de cobertura
    # - cambio de forma de pago
    # - cancelación parcial
    # etc.
    aplicar_efectos_endoso(endoso=endoso, poliza=poliza, usuario=usuario)

    log_poliza_event(
        poliza=poliza,
        tipo="ENDOSO",
        titulo=f"Endoso aplicado: {endoso.get_tipo_endoso_display()}",
        detalle=construir_descripcion_evento_endoso(endoso),
        data={
            "accion": "crear",
            "endoso_id": endoso.id,
            "tipo_endoso": endoso.tipo_endoso,
            "tipo_endoso_label": endoso.get_tipo_endoso_display(),
            "prima_ajuste": str(endoso.prima_ajuste),
            "fecha": endoso.fecha.isoformat() if endoso.fecha else None,
            "documento_id": endoso.documento_id,
            "descripcion": endoso.descripcion,
        },
        actor=usuario,
        dedupe_key=f"ENDOSO:CREATE:{endoso.id}",
    )

    return endoso


def aplicar_efectos_endoso(*, endoso, poliza, usuario=None):
    """
    Punto central para aplicar efectos de negocio sobre la póliza.

    Por ahora lo dejamos preparado.
    Aquí podrás agregar más adelante reglas como:
    - actualizar forma de pago
    - marcar cancelación parcial
    - actualizar datos del vehículo
    - modificar datos del asegurado
    """
    if endoso.tipo_endoso == Endoso.Tipo.CANCELACION_PARCIAL:
        # Ejemplo futuro:
        # poliza.estatus = Poliza.Estatus.CANCELADA
        # poliza.save(update_fields=["estatus"])
        pass

    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_FORMA_PAGO:
        # Ejemplo futuro:
        # actualizar plan / periodicidad de pago
        pass

    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_COBERTURA:
        # Ejemplo futuro:
        # actualizar cobertura / regenerar cálculo
        pass

    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_VEHICULO:
        # Ejemplo futuro:
        # actualizar vehículo asociado
        pass

    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_DATOS:
        # Ejemplo futuro:
        # actualizar datos administrativos
        pass

    elif endoso.tipo_endoso == Endoso.Tipo.OTRO:
        pass


def construir_descripcion_evento_endoso(endoso):
    """
    Genera una descripción legible para la bitácora.
    """
    partes = [f"Tipo: {endoso.get_tipo_endoso_display()}"]

    if endoso.prima_ajuste > 0:
        partes.append(f"Prima ajuste: +{endoso.prima_ajuste}")
    elif endoso.prima_ajuste < 0:
        partes.append(f"Prima ajuste: {endoso.prima_ajuste}")
    else:
        partes.append("Prima ajuste: 0.00")

    if endoso.fecha:
        partes.append(f"Fecha: {endoso.fecha}")

    if endoso.descripcion:
        partes.append(f"Descripción: {endoso.descripcion}")

    if endoso.documento_id:
        partes.append("Documento adjunto: Sí")

    return " | ".join(partes)


def aplicar_efectos_endoso(*, endoso, poliza, usuario=None):
    if endoso.tipo_endoso == Endoso.Tipo.CANCELACION_PARCIAL:
        pass
    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_FORMA_PAGO:
        pass
    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_COBERTURA:
        pass
    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_VEHICULO:
        pass
    elif endoso.tipo_endoso == Endoso.Tipo.CAMBIO_DATOS:
        pass
    elif endoso.tipo_endoso == Endoso.Tipo.OTRO:
        pass


# Endosos Editar y Eliminar
@transaction.atomic
def editar_endoso(
    *,
    endoso,
    tipo_endoso,
    descripcion="",
    prima_ajuste=0,
    fecha=None,
    documento=None,
    usuario=None,
):
    # traer estado original desde BD
    endoso_db = Endoso.objects.get(pk=endoso.pk)
    antes = snapshot_endoso(endoso_db)
    
    if fecha is None:
        fecha = timezone.localdate()

    if prima_ajuste in (None, ""):
        prima_ajuste = Decimal("0.00")
    else:
        prima_ajuste = Decimal(str(prima_ajuste))

    endoso.tipo_endoso = tipo_endoso
    endoso.descripcion = descripcion or ""
    endoso.prima_ajuste = prima_ajuste
    endoso.fecha = fecha
    endoso.documento = documento
    endoso.save()

    despues = snapshot_endoso(endoso)

    log_poliza_event(
        poliza=endoso.poliza,
        tipo="ENDOSO_EDITADO",
        titulo=f"Endoso editado: {endoso.get_tipo_endoso_display()}",
        detalle="Se actualizaron datos del endoso.",
        data={
            "accion": "editar",
            "endoso_id": endoso.id,
            "antes": antes,
            "despues": despues,
        },
        actor=usuario,
        dedupe_key=f"ENDOSO:UPDATE:{endoso.id}:{endoso.updated_at.timestamp()}",
    )

    return endoso


def eliminar_endoso(*, endoso, usuario=None):
    poliza = endoso.poliza
    documento = endoso.documento
    endoso_id = endoso.id
    tipo_label = endoso.get_tipo_endoso_display()

    # 🔥 guardar referencia antes de borrar
    if documento:
        archivo = documento.file
        documento.delete()  # borra DB

        if archivo:
            archivo.delete(save=False)  # borra archivo físico

    endoso.delete()

    log_poliza_event(
        poliza=poliza,
        tipo="ENDOSO_ELIMINADO",
        titulo=f"Endoso eliminado: {tipo_label}",
        detalle=f"Se eliminó el endoso #{endoso_id} junto con su documento.",
        actor=usuario,
        dedupe_key=f"ENDOSO_DELETE:{endoso_id}",
    )


def snapshot_endoso(endoso):
    return {
        "id": endoso.id,
        "tipo_endoso": endoso.tipo_endoso,
        "tipo_endoso_label": endoso.get_tipo_endoso_display(),
        "descripcion": endoso.descripcion,
        "prima_ajuste": str(endoso.prima_ajuste),
        "fecha": endoso.fecha.isoformat() if endoso.fecha else None,
        "documento_id": endoso.documento_id,
    }


def construir_detalle_edicion_endoso(antes, despues):
    cambios = []

    campos = [
        ("tipo_endoso_label", "Tipo"),
        ("fecha", "Fecha"),
        ("prima_ajuste", "Prima ajuste"),
        ("descripcion", "Descripción"),
        ("documento_id", "Documento"),
    ]

    for key, label in campos:
        valor_antes = antes.get(key)
        valor_despues = despues.get(key)
        if valor_antes != valor_despues:
            cambios.append(f"{label}: '{valor_antes}' → '{valor_despues}'")

    if not cambios:
        return "Se guardó el endoso sin cambios relevantes."

    return " | ".join(cambios)

