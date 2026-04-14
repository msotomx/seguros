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
from ui.services.perms import can_manage_pago, can_see_pagos, pagos_visibles_para_usuario
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
        pago.monto_pagado = pago.monto
        pago.estatus = Pago.Estatus.PAGADO
        pago.save(update_fields=["metodo", "referencia", "fecha_pago", "monto_pagado", "estatus", "updated_at"])

        log_poliza_event(
            poliza=pago.poliza,
            tipo=PolizaEvento.Tipo.PAGO_PAGADO,
            actor=request.user,
            titulo="Pago confirmado manualmente",
            detalle=f"Se confirmó manualmente el pago #{pago.id} por {pago.moneda} {pago.monto}.",
            data={
                "pago_id": pago.id,
                "fecha_programada": str(pago.fecha_programada),
                "fecha_pago": str(pago.fecha_pago) if pago.fecha_pago else "",
                "metodo": pago.metodo,
                "referencia": pago.referencia,
                "monto": str(pago.monto),
                "moneda": pago.moneda,
                "origen": "manual",
            },
            dedupe_key=f"PAGO_PAGADO:{pago.id}",
        )
            
    messages.success(request, "Pago confirmado manualmente.")
    return redirect(request.META.get("HTTP_REFERER") or "ui:pago_list")


class PagoListView(LoginRequiredMixin, ListView):
    model = Pago
    template_name = "ui/finanzas/pago_list.html"
    context_object_name = "pagos"
    paginate_by = 25
    
    def get_queryset(self):
        qs = (
            Pago.objects
            .select_related("poliza", "cliente", "comprobante")
            .order_by("-fecha_programada", "-id")
        )

        qs = pagos_visibles_para_usuario(self.request.user, qs)

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

        ultimos = (self.request.GET.get("ultimos") or "").strip()
        if ultimos:
            dias = int(ultimos)
            fecha_inicio = timezone.localdate() - timedelta(days=dias)

            qs = qs.filter(
                estatus=Pago.Estatus.PAGADO,
                fecha_pago__gte=fecha_inicio
            )

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

from ui.services.validar import validar_archivo_comprobante
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from documentos.models import Documento
from finanzas.models import Pago
from polizas.models import PolizaEvento
from polizas.services import log_poliza_event


def detectar_tipo_documento(uploaded_file):
    content_type = (uploaded_file.content_type or "").lower()

    if content_type == "application/pdf":
        return Documento.Tipo.PDF

    if content_type in {"image/jpeg", "image/png"}:
        return Documento.Tipo.IMG

    return Documento.Tipo.OTRO


@login_required
@require_POST
def pago_comprobante_subir(request, pk):
    pago = get_object_or_404(
        Pago.objects.select_related("poliza", "cliente", "comprobante"),
        pk=pk,
    )

    # Permisos: Admin/Supervisor (finanzas) o agente dueño de la póliza
    if not can_manage_pago(request.user, pago):
        messages.error(request, "No tienes permisos para adjuntar comprobante a este pago.")
        return redirect(request.META.get("HTTP_REFERER") or "ui:pago_list")

    archivo = request.FILES.get("archivo")

    try:
        validar_archivo_comprobante(archivo)
    except ValidationError as exc:
        messages.success(request, str(exc))  # exc.message
        return redirect(request.META.get("HTTP_REFERER") or "ui:pago_list")

    comprobante_anterior_id = pago.comprobante_id
    
    try:
        with transaction.atomic():
            documento = Documento.objects.create(
                nombre_archivo=archivo.name,
                tipo=detectar_tipo_documento(archivo),
                file=archivo,
                tamano=archivo.size,
                subido_por=request.user,
            )

            pago.comprobante = documento
            pago.save(update_fields=["comprobante", "updated_at"])

            # Hay comprobante anterior
            if comprobante_anterior_id:
                log_poliza_event(
                    poliza=pago.poliza,
                    tipo=PolizaEvento.Tipo.PAGO_COMPROBANTE_REEMPLAZADO,
                    actor=request.user,
                    titulo="Comprobante reemplazado",
                    detalle=f"Se reemplazó el comprobante del pago #{pago.id}.",
                    data={
                        "pago_id": pago.id,
                        "documento_id_anterior": comprobante_anterior_id,
                        "documento_id_nuevo": pago.comprobante_id,
                        "nombre_archivo": documento.nombre_archivo,
                        "tipo_documento": documento.tipo,
                        "fecha_programada": str(pago.fecha_programada) if pago.fecha_programada else "",
                        "fecha_pago": str(pago.fecha_pago) if pago.fecha_pago else "",
                        "monto": str(pago.monto),
                        "moneda": pago.moneda,
                        "metodo": pago.metodo,
                        "referencia": pago.referencia,
                    },
                    dedupe_key=f"PAGO_COMPROBANTE_REEMPLAZADO:{pago.id}:{pago.comprobante_id}",
                )
                messages.success(request, "Comprobante reemplazado correctamente.")
            else:
                log_poliza_event(
                    poliza=pago.poliza,
                    tipo=PolizaEvento.Tipo.PAGO_COMPROBANTE_ADJUNTADO,
                    actor=request.user,
                    titulo="Comprobante adjuntado al pago",
                    detalle=f"Se adjuntó comprobante al pago #{pago.id}.",
                    data={
                        "pago_id": pago.id,
                        "documento_id": pago.comprobante_id,
                        "nombre_archivo": documento.nombre_archivo,
                        "tipo_documento": documento.tipo,
                        "fecha_programada": str(pago.fecha_programada) if pago.fecha_programada else "",
                        "fecha_pago": str(pago.fecha_pago) if pago.fecha_pago else "",
                        "monto": str(pago.monto),
                        "moneda": pago.moneda,
                        "metodo": pago.metodo,
                        "referencia": pago.referencia,
                    },
                    dedupe_key=f"PAGO_COMPROBANTE_ADJUNTADO:{pago.id}:{pago.comprobante_id}",
                )
                messages.success(request, "Comprobante adjuntado correctamente.")
                
    except Exception as exc:
        messages.error(request, f"No fue posible adjuntar el comprobante: {exc}")
        return redirect(request.META.get("HTTP_REFERER") or "ui:pago_list")

    return redirect(request.META.get("HTTP_REFERER") or "ui:pago_list")
