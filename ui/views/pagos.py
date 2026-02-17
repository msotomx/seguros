from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView
from django.utils.timezone import localdate
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.db import transaction
from datetime import date
from django.utils.dateparse import parse_date

from polizas.models import PolizaEvento
from polizas.services import log_poliza_event
from ui.services.perms import can_manage_pago, can_see_pagos
from finanzas.models import Pago
from documentos.models import Documento


@login_required
@require_POST
def pago_marcar_pagado(request, pk):
    pago = get_object_or_404(Pago.objects.select_related("poliza"), pk=pk)

    if not can_manage_pago(request.user, pago):
        messages.error(request, "No tienes permisos para actualizar este pago.")
        return redirect("ui:pago_list")

    if pago.estatus == Pago.Estatus.PAGADO:
        messages.info(request, "Este pago ya está marcado como pagado.")
        return redirect("ui:pago_list")

    metodo = (request.POST.get("metodo") or "").strip()
    referencia = (request.POST.get("referencia") or "").strip()
    fecha_pago = request.POST.get("fecha_pago") or ""

    # fecha por defecto = hoy
    fecha_pago_raw = (request.POST.get("fecha_pago") or "").strip()
    fecha_pago = parse_date(fecha_pago_raw) if fecha_pago_raw else localdate()

    with transaction.atomic():
        pago.metodo = metodo
        pago.referencia = referencia
        pago.fecha_pago = fecha_pago
        pago.estatus = Pago.Estatus.PAGADO
        pago.save(update_fields=["metodo", "referencia", "fecha_pago", "estatus", "updated_at"])

        log_poliza_event(
            poliza=pago.poliza,
            tipo=PolizaEvento.Tipo.PAGO_PAGADO,
            actor=request.user,
            titulo="Pago marcado como pagado",
            data={
                "pago_id": pago.id,
                "fecha_programada": str(pago.fecha_programada),
                "fecha_pago": str(pago.fecha_pago) if pago.fecha_pago else "",
                "metodo": pago.metodo,
                "referencia": pago.referencia,
                "monto": str(pago.monto),
            },
        )


    messages.success(request, "Pago marcado como pagado.")
    return redirect(request.META.get("HTTP_REFERER") or "ui:pago_list")


class PagoListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/finanzas/pago_list.html"
    context_object_name = "pagos"
    paginate_by = 25
    
    def get_queryset(self):
        qs = (
            Pago.objects
            .select_related("poliza", "poliza__cliente", "poliza__aseguradora")
            .order_by("fecha_programada", "-created_at")
        )

        user = self.request.user
        # Alcance: agente ve sus pólizas; supervisor/admin ve todo

        if not can_see_pagos(user):
            qs = qs.filter(poliza__agente=user)

        # Filtros
        q = (self.request.GET.get("q") or "").strip()
        estatus = (self.request.GET.get("estatus") or "").strip()
        desde = (self.request.GET.get("desde") or "").strip()
        hasta = (self.request.GET.get("hasta") or "").strip()

        if q:
            qs = qs.filter(
                Q(poliza__numero_poliza__icontains=q) |
                Q(poliza__cliente__nombre__icontains=q) |
                Q(poliza__cliente__nombre_comercial__icontains=q) |
                Q(referencia__icontains=q)
            )

        if estatus:
            qs = qs.filter(estatus=estatus)

        if desde:
            qs = qs.filter(fecha_programada__gte=desde)

        if hasta:
            qs = qs.filter(fecha_programada__lte=hasta)

        # Auto “Vencido” (opcional visual, sin guardar): solo filtra si lo pides
        # Nota: lo correcto es tener un job que marque vencidos.
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "estatus": self.request.GET.get("estatus", ""),
            "desde": self.request.GET.get("desde", ""),
            "hasta": self.request.GET.get("hasta", ""),
        }
        ctx["estatus_choices"] = Pago.Estatus.choices
        ctx["can_see_pagos"] = can_see_pagos(self.request.user)
        
        return ctx

@login_required
@require_POST
def pago_comprobante_subir(request, pk):
    pago = get_object_or_404(Pago.objects.select_related("poliza"), pk=pk)

    # Permisos: Admin/Supervisor (finanzas) o agente dueño de la póliza
    if not (can_manage_pago(request.user, pago) or pago.poliza.agente_id == request.user.id):
        messages.error(request, "No tienes permisos para adjuntar comprobante a este pago.")
        return redirect("ui:pago_list")

    archivo = request.FILES.get("archivo")
    if not archivo:
        messages.error(request, "Selecciona un archivo para subir.")
        return redirect("ui:pago_list")

    # Permitir PDF e imágenes (jpg/png)
    ok_types = {"application/pdf", "image/jpeg", "image/png"}
    ctype = (archivo.content_type or "").lower()
    if ctype and ctype not in ok_types:
        messages.error(request, "Solo se permite PDF, JPG o PNG.")
        return redirect("ui:pago_list")

    # Tipo Documento
    if ctype == "application/pdf" or archivo.name.lower().endswith(".pdf"):
        tipo = Documento.Tipo.PDF
    elif archivo.name.lower().endswith((".jpg", ".jpeg", ".png")):
        tipo = Documento.Tipo.IMG
    else:
        tipo = Documento.Tipo.OTRO

    with transaction.atomic():
        doc = Documento.objects.create(
            nombre_archivo=(request.POST.get("nombre_archivo") or archivo.name).strip() or archivo.name,
            tipo=tipo,
            file=archivo,
            tamano=getattr(archivo, "size", 0) or 0,
            subido_por=request.user,
        )

        anterior_id = pago.comprobante_id
        pago.comprobante = doc
        pago.save(update_fields=["comprobante", "updated_at"])

        # Bitácora en póliza (recomendado)
        log_poliza_event(
            poliza=pago.poliza,
            tipo=getattr(PolizaEvento.Tipo, "PAGO_COMPROBANTE_ADJUNTADO", PolizaEvento.Tipo.CREADA),
            actor=request.user,
            titulo="Comprobante de pago adjuntado",
            data={
                "pago_id": pago.id,
                "documento_id": doc.id,
                "nombre_archivo": doc.nombre_archivo,
                "reemplazo_de": anterior_id,
                "fecha_programada": str(pago.fecha_programada),
                "monto": str(pago.monto),
            },
        )

    messages.success(request, "Comprobante adjuntado correctamente.")
    return redirect("ui:pago_list")
