from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from documentos.models import Documento
from crm.models import Cliente
from polizas.models import Poliza, Endoso
from finanzas.models import Pago
from polizas.services import log_poliza_event
from django.contrib import messages

@login_required
def documento_download(request, pk: int):
    doc = get_object_or_404(Documento, pk=pk)

    # Permiso base (si aún no lo estás asignando a clientes portal, puedes relajarlo temporalmente)
    if not request.user.has_perm("documentos.download_documento"):
        raise PermissionDenied("No tienes permiso para descargar documentos.")

    # Admin/Supervisor: acceso total
    if request.user.is_superuser or request.user.groups.filter(name__in=["Admin", "Supervisor"]).exists():
        return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.nombre_archivo)

    # Buscar si el doc es la póliza PDF
    pol = (
        Poliza.objects
        .filter(documento_id=doc.id)
        .select_related("cliente")
        .first()
    )
    if pol:
        # Cliente portal: solo sus pólizas
        if Cliente.objects.filter(user_portal=request.user, portal_activo=True, id=pol.cliente_id).exists():
            return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.nombre_archivo)

        # Agente: solo su cartera
        if pol.agente_id == request.user.id:
            return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.nombre_archivo)

        raise PermissionDenied("No autorizado.")

    # Buscar si el doc es comprobante de pago
    pago = (
        Pago.objects
        .filter(comprobante_id=doc.id)
        .select_related("poliza__cliente")
        .first()
    )
    if pago:
        # Cliente portal: solo sus pagos
        if Cliente.objects.filter(user_portal=request.user, portal_activo=True, id=pago.poliza.cliente_id).exists():
            return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.nombre_archivo)

        # Agente: solo su cartera
        if pago.poliza.agente_id == request.user.id:
            return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.nombre_archivo)

        raise PermissionDenied("No autorizado.")

    # Documento huérfano
    raise PermissionDenied("Documento no ligado a póliza/pago.")


# Subir comprobante de Endoso
import hashlib

def subir_endoso_pdf(request, endoso_id):
    endoso = get_object_or_404(Endoso, id=endoso_id)

    archivo = request.FILES.get("archivo")

    if not archivo:
        messages.error(request, "Debes seleccionar un archivo.")
        return redirect("ui:poliza_detail", pk=endoso.poliza_id)

    # 🔹 calcular hash (opcional pero PRO)
    hash_archivo = hashlib.sha256(archivo.read()).hexdigest()
    archivo.seek(0)  # regresa el puntero)

    doc = Documento.objects.create(
        nombre_archivo=archivo.name,
        tipo=Documento.Tipo.OTRO,  # o puedes crear tipo ENDOSO
        file=archivo,
        tamano=archivo.size,
        hash=hash_archivo,
        subido_por=request.user if request.user.is_authenticated else None,
    )

    # 🔹 ligar documento al endoso
    endoso.documento = doc
    endoso.save(update_fields=["documento", "updated_at"])

    # 🔹 evento en bitácora
    log_poliza_event(
        poliza=endoso.poliza,
        tipo="ENDOSO_COMPROBANTE_ADJUNTADO",
        titulo="Documento adjuntado a endoso",
        detalle=f"Se adjuntó documento al endoso {endoso.get_tipo_endoso_display()}",
        data={
            "endoso_id": endoso.id,
            "documento_id": doc.id,
            "nombre_archivo": doc.nombre_archivo,
        },
        actor=request.user,
        dedupe_key=f"ENDOSO_DOC:{endoso.id}:{doc.id}",
    )

    messages.success(request, "Documento adjuntado correctamente.")
    return redirect("ui:poliza_detail", pk=endoso.poliza_id)

import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from documentos.models import Documento

# Usado en Ver Documento en Endoso, PolizaDetail, PolizaList
@login_required
def ver_documento(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)

    if not documento.file:
        raise Http404("Documento no encontrado")

    try:
        return FileResponse(
            documento.file.open("rb"),
            content_type="application/pdf"
        )
    except FileNotFoundError:
        raise Http404("Archivo no existe")
