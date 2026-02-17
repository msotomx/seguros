from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from documentos.models import Documento
from crm.models import Cliente
from polizas.models import Poliza
from finanzas.models import Pago


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
