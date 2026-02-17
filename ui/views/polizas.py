from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from django.views.generic import ListView, DetailView

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import localdate
from django.views.decorators.http import require_POST
from datetime import timedelta, datetime
from django.utils import timezone

from polizas.services import log_poliza_event
from ui.services.perms import can_manage_poliza
from ui.services.perms import can_update_poliza_numero, can_admin_polizas

from polizas.models import PolizaEvento
from polizas.models import Poliza
from finanzas.models import Pago, Comision
from documentos.models import Documento
from documentos.views import documento_download


def _is_admin(user) -> bool:
    return user.is_superuser or user.groups.filter(name="Admin").exists()

class PolizaListView(LoginRequiredMixin, ListView):
    model = Poliza
    template_name = "ui/polizas/poliza_list.html"
    context_object_name = "polizas"
    paginate_by = 20

    def get_queryset(self):
        qs = Poliza.objects.select_related(
            "cliente", "aseguradora", "producto", "vehiculo", "flotilla", "agente"
        ).order_by("-created_at", "-id")

        vencen = (self.request.GET.get("vencen") or "").strip()
        if vencen.isdigit():
            days = int(vencen)
            today = localdate()
            until = today + timedelta(days=days)
            qs = qs.filter(
                estatus=Poliza.Estatus.VIGENTE,
                vigencia_hasta__gte=today,
                vigencia_hasta__lte=until,
            )

        user = self.request.user
        if user.groups.filter(name="Agente").exists():
            qs = qs.filter(agente=user)

        # Filtros q/estatus/desde/hasta como ya los tienes...
        # Filtros por querystring
        q = (self.request.GET.get("q") or "").strip()
        estatus = (self.request.GET.get("estatus") or "").strip()
        desde = (self.request.GET.get("desde") or "").strip()
        hasta = (self.request.GET.get("hasta") or "").strip()

        if q:
            qs = qs.filter(
                Q(numero_poliza__icontains=q)
                | Q(cliente__nombre__icontains=q)
                | Q(cliente__nombre_comercial__icontains=q)
                | Q(cliente__rfc__icontains=q)
            )

        if estatus:
            qs = qs.filter(estatus=estatus)

        # fecha_emision es DateField (no DateTime), así que no uses __date
        if desde:
            qs = qs.filter(fecha_emision__gte=desde)

        if hasta:
            qs = qs.filter(fecha_emision__lte=hasta)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "estatus": self.request.GET.get("estatus", ""),
            "desde": self.request.GET.get("desde", ""),
            "hasta": self.request.GET.get("hasta", ""),
        }
        # Choices para dropdown
        ctx["estatus_choices"] = getattr(Poliza, "Estatus", None).choices if hasattr(Poliza, "Estatus") else []
        return ctx

class PolizaDetailView(LoginRequiredMixin, DetailView):
    model = Poliza
    template_name = "ui/polizas/poliza_detail.html"
    context_object_name = "poliza"

    def get_queryset(self):
        qs = Poliza.objects.select_related(
            "cliente", "aseguradora", "producto", "vehiculo", "flotilla", "agente", "documento"
        )

        user = self.request.user
        if user.groups.filter(name="Agente").exists():
            qs = qs.filter(agente=user)

        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        poliza = ctx["poliza"]
        ctx["eventos"] = poliza.eventos.select_related("actor").all()[:50]
        ctx["ult_pagos"] = poliza.pagos.order_by("fecha_programada")[:6]
        ctx["comision"] = poliza.comisiones.order_by("-created_at").first()
        ctx["can_admin_polizas"] = can_admin_polizas(self.request.user)

        # --- PAGOS ---
        pagos_qs = poliza.pagos.all().order_by("fecha_programada")
        pagos_sum = pagos_qs.aggregate(
            total=Sum("monto"),
            pagado=Sum("monto", filter=Q(estatus=Pago.Estatus.PAGADO)),
            pendiente=Sum("monto", filter=Q(estatus=Pago.Estatus.PENDIENTE)),
            vencido=Sum("monto", filter=Q(estatus=Pago.Estatus.VENCIDO)),
        )
        pagos_total = pagos_sum["total"] or 0
        pagos_pagado = pagos_sum["pagado"] or 0
        pagos_pendiente = pagos_sum["pendiente"] or 0
        pagos_vencido = pagos_sum["vencido"] or 0
        pagos_saldo = (pagos_total or 0) - (pagos_pagado or 0)

        # Últimos / próximos pagos (para vista rápida)
        ult_pagos = pagos_qs.order_by("-fecha_programada")[:5]
        prox_pagos = pagos_qs.filter(estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.VENCIDO]).order_by("fecha_programada")[:5]

        # --- COMISIONES ---
        com_qs = poliza.comisiones.all().order_by("-created_at")
        com_sum = com_qs.aggregate(
            total=Sum("monto"),
            pagada=Sum("monto", filter=Q(estatus=Comision.Estatus.PAGADA)),
            pendiente=Sum("monto", filter=Q(estatus=Comision.Estatus.PENDIENTE)),
        )
        com_total = com_sum["total"] or 0
        com_pagada = com_sum["pagada"] or 0
        com_pendiente = com_sum["pendiente"] or 0
        ultima_comision = com_qs.first()

        ctx["fin"] = {
            "pagos": {
                "total": pagos_total,
                "pagado": pagos_pagado,
                "pendiente": pagos_pendiente,
                "vencido": pagos_vencido,
                "saldo": pagos_saldo,
                "ult": ult_pagos,
                "prox": prox_pagos,
            },
            "comisiones": {
                "total": com_total,
                "pagada": com_pagada,
                "pendiente": com_pendiente,
                "ultima": ultima_comision,
            },
        }
        return ctx


from finanzas.services.pagos import crear_plan_pagos
from finanzas.services.comisiones import crear_comision_poliza

@login_required
@require_POST
def poliza_marcar_vigente(request, pk):
    poliza = get_object_or_404(Poliza, pk=pk)

    # Permisos por agente 
    if not can_manage_poliza(request.user, poliza):
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # Ya vigente → idempotente
    if poliza.estatus == Poliza.Estatus.VIGENTE:
        messages.info(request, "La póliza ya está marcada como vigente.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # BLOQUEO CLAVE
    if poliza.numero_poliza.startswith("TEMP-"):
        messages.error(
            request,
            "No se puede marcar como vigente una póliza con número temporal. "
            "Captura primero el número real de póliza."
        )
        return redirect("ui:poliza_detail", pk=poliza.pk)

    with transaction.atomic():
        poliza.estatus = Poliza.Estatus.VIGENTE
        poliza.fecha_emision = poliza.fecha_emision or localdate()
        poliza.save()

        # crear pagos después
        n = crear_plan_pagos(poliza, overwrite=False)
        # genera comisiones de la poliza
        crear_comision_poliza(poliza, overwrite=False)

        # Actualizar Bitacora de Eventos
        log_poliza_event(
            poliza=poliza,
            tipo=PolizaEvento.Tipo.MARCADA_VIGENTE,
            actor=request.user,
            titulo="Póliza marcada como vigente",
            data={"fecha_emision": str(poliza.fecha_emision)},
        )

    messages.success(request, "Póliza marcada como vigente.")
    return redirect("ui:poliza_detail", pk=poliza.pk)


@login_required
@require_POST
def poliza_actualizar_numero(request, pk):
    poliza = get_object_or_404(Poliza, pk=pk)

    if not can_update_poliza_numero(request.user, poliza):
        messages.error(request, "No tienes permisos para modificar el número de póliza.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    nuevo = (request.POST.get("numero_poliza") or "").strip().upper()

    if not nuevo:
        messages.error(request, "Captura el número de póliza.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    if nuevo.startswith("TEMP-"):
        messages.error(request, "El número real no debe iniciar con TEMP-.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    anterior = poliza.numero_poliza

    if nuevo == anterior:
        messages.info(request, "No hubo cambios en el número de póliza.")
        return redirect("ui:poliza_detail", pk=poliza.pk)
    try:
        with transaction.atomic():
            poliza.numero_poliza = nuevo
            poliza.save(update_fields=["numero_poliza", "updated_at"])

            log_poliza_event(
                poliza=poliza,
                tipo=PolizaEvento.Tipo.NUMERO_ACTUALIZADO,
                actor=request.user,
                titulo="Número de póliza actualizado",
                data={"antes": anterior, "despues": nuevo},
            )

    except IntegrityError:
        # Por tu UniqueConstraint: (aseguradora, numero_poliza)
        messages.error(
            request,
            f"Ya existe una póliza con ese número para {poliza.aseguradora.nombre}."
        )
        return redirect("ui:poliza_detail", pk=poliza.pk)

    messages.success(request, "Número de póliza actualizado.")
    return redirect("ui:poliza_detail", pk=poliza.pk)


@login_required
@require_POST
def poliza_actualizar_numero2(request, pk):
    poliza = get_object_or_404(Poliza.objects.select_related("aseguradora"), pk=pk)

    # Permisos / alcance 
    if not can_manage_poliza(request.user, poliza):
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # Regla: solo permitir capturar/editar número cuando está EN_PROCESO
    if poliza.estatus != Poliza.Estatus.EN_PROCESO:
        messages.error(request, "Solo puedes cambiar el número cuando la póliza está en proceso.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    numero = (request.POST.get("numero_poliza") or "").strip()

    if not numero:
        messages.error(request, "Captura el número real de póliza.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    if numero.startswith("TEMP-"):
        messages.error(request, "El número real no puede iniciar con TEMP-.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # (Opcional) normalizar: quitar espacios internos dobles, etc.
    # numero = " ".join(numero.split())

    try:
        with transaction.atomic():
            poliza.numero_poliza = numero
            poliza.save()  # respeta updated_at

            # Actualizar Bitacora de Eventos
            old = poliza.numero_poliza
            poliza.numero_poliza = numero
            poliza.save()

            log_poliza_event(
                poliza=poliza,
                tipo=PolizaEvento.Tipo.NUMERO_ACTUALIZADO,
                actor=request.user,
                titulo="Número de póliza actualizado",
                data={"antes": old, "despues": numero},
            )

    except IntegrityError:
        # Por tu UniqueConstraint: (aseguradora, numero_poliza)
        messages.error(
            request,
            f"Ya existe una póliza con ese número para {poliza.aseguradora.nombre}."
        )
        return redirect("ui:poliza_detail", pk=poliza.pk)

    messages.success(request, "Número de póliza actualizado.")
    return redirect("ui:poliza_detail", pk=poliza.pk)


@login_required
@require_POST
def poliza_cancelar(request, pk):
    poliza = get_object_or_404(Poliza, pk=pk)

    # Permisos / alcance
    if not can_manage_poliza(request.user, poliza):
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # Validaciones de estatus
    if poliza.estatus == Poliza.Estatus.CANCELADA:
        messages.info(request, "La póliza ya está cancelada.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    if poliza.estatus == Poliza.Estatus.VENCIDA:
        messages.error(request, "No se puede cancelar una póliza vencida.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    if poliza.estatus != Poliza.Estatus.VIGENTE:
        messages.error(request, "Solo se puede cancelar una póliza vigente.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    motivo = (request.POST.get("motivo_cancelacion") or "").strip()
    detalle = (request.POST.get("motivo_cancelacion_detalle") or "").strip()

    if not motivo:
        messages.error(request, "Selecciona un motivo de cancelación.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    with transaction.atomic():
        poliza.estatus = Poliza.Estatus.CANCELADA
        poliza.fecha_cancelacion = localdate()
        poliza.motivo_cancelacion = motivo
        poliza.motivo_cancelacion_detalle = detalle
        poliza.save()

        # Cambia estatus de Pagos a Cancelado
        poliza.pagos.filter(
            estatus__in=[Pago.Estatus.PENDIENTE, Pago.Estatus.VENCIDO]
        ).update(estatus=Pago.Estatus.CANCELADO)

        # Actualizar Bitacora de Eventos
        log_poliza_event(
            poliza=poliza,
            tipo=PolizaEvento.Tipo.CANCELADA,
            actor=request.user,
            titulo="Póliza cancelada",
            data={
                "fecha_cancelacion": str(poliza.fecha_cancelacion),
                "motivo": motivo, 
                "detalle": detalle
            },
        )

    messages.success(request, "La póliza fue cancelada correctamente.")
    return redirect("ui:poliza_detail", pk=poliza.pk)


def _add_one_year_minus_one_day(start_date):
    """
    Regla de vigencia: 1 año menos 1 día.
    Si quieres “mismo día del siguiente año” exacto, lo cambiamos.
    """
    # Evitamos dateutil para mantenerlo simple: 365 días funciona para mayoría,
    return start_date + timedelta(days=365) - timedelta(days=1)


@login_required
@require_POST
def poliza_renovar(request, pk):
    poliza = get_object_or_404(
        Poliza.objects.select_related("aseguradora", "cliente"),
        pk=pk
    )

    # 1) Permisos / alcance
    if not can_manage_poliza(request.user, poliza):
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # 2) Validar estatus
    if poliza.estatus == Poliza.Estatus.CANCELADA:
        messages.error(request, "No se puede renovar una póliza cancelada.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    if poliza.estatus not in [Poliza.Estatus.VIGENTE, Poliza.Estatus.VENCIDA]:
        messages.error(request, "Solo se puede renovar una póliza vigente o vencida.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # 3) Calcular nueva vigencia
    nueva_desde = poliza.vigencia_hasta + timedelta(days=1)
    nueva_hasta = nueva_desde + timedelta(days=365)

    # 4) Validar que no exista ya una renovación
    existe = Poliza.objects.filter(
        cliente=poliza.cliente,
        aseguradora=poliza.aseguradora,
        producto=poliza.producto,
        vehiculo=poliza.vehiculo,
        flotilla=poliza.flotilla,
        vigencia_desde=nueva_desde,
    ).exclude(estatus=Poliza.Estatus.CANCELADA).exists()

    if existe:
        messages.error(
            request,
            "Ya existe una renovación creada para la siguiente vigencia."
        )
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # 5) Crear la nueva póliza
    numero_temp = f"TEMP-REN-{poliza.id}-{localdate().strftime('%Y%m%d%H%M%S')}"
    
    agente = poliza.agente or request.user

    with transaction.atomic():
        nueva = Poliza.objects.create(
            cliente=poliza.cliente,
            vehiculo=poliza.vehiculo,
            flotilla=poliza.flotilla,
            aseguradora=poliza.aseguradora,
            producto=poliza.producto,
            cotizacion_item=None,
            numero_poliza=numero_temp,
            fecha_emision=None,
            vigencia_desde=nueva_desde,
            vigencia_hasta=nueva_hasta,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_total=poliza.prima_total,
            forma_pago=poliza.forma_pago or "",
            agente=agente,
        )

        # Actualizar Bitacora de Eventos
        log_poliza_event(
            poliza=poliza,
            tipo=PolizaEvento.Tipo.RENOVADA,
            actor=request.user,
            titulo="Renovación creada",
            data={"poliza_nueva_id": nueva.id, "vigencia_desde": str(nueva.vigencia_desde), "vigencia_hasta": str(nueva.vigencia_hasta)},
        )

        log_poliza_event(
            poliza=nueva,
            tipo=PolizaEvento.Tipo.CREADA,
            actor=request.user,
            titulo="Póliza creada por renovación",
            data={"poliza_origen_id": poliza.id},
        )

    messages.success(
        request,
        "Renovación creada. Captura el número real y marca como vigente cuando esté emitida."
    )
    return redirect("ui:poliza_detail", pk=nueva.pk)

def _parse_date(value: str):
    # value viene como 'YYYY-MM-DD'
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


@login_required
@require_POST
def poliza_actualizar_vigencia(request, pk):
    poliza = get_object_or_404(Poliza, pk=pk)

    # Permisos / alcance
    if not can_manage_poliza(request.user, poliza):
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # Regla: solo EN_PROCESO
    if poliza.estatus != Poliza.Estatus.EN_PROCESO:
        messages.error(request, "Solo puedes modificar la vigencia cuando la póliza está en proceso.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    desde_raw = (request.POST.get("vigencia_desde") or "").strip()
    hasta_raw = (request.POST.get("vigencia_hasta") or "").strip()

    vigencia_desde = _parse_date(desde_raw)
    vigencia_hasta = _parse_date(hasta_raw)

    if not vigencia_desde or not vigencia_hasta:
        messages.error(request, "Fechas inválidas. Verifica el formato.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    if vigencia_hasta < vigencia_desde:
        messages.error(request, "La vigencia hasta no puede ser menor que la vigencia desde.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # (Opcional) advertencia si no es ~365 días, sin bloquear
    dias = (vigencia_hasta - vigencia_desde).days + 1  # inclusivo
    if dias < 300 or dias > 400:
        messages.warning(request, f"Revisa la vigencia: el rango es de {dias} días.")

    with transaction.atomic():
        poliza.vigencia_desde = vigencia_desde
        poliza.vigencia_hasta = vigencia_hasta
        poliza.save()

        # Actualizar Bitacora de Eventos
        old_desde, old_hasta = poliza.vigencia_desde, poliza.vigencia_hasta
        poliza.vigencia_desde = vigencia_desde
        poliza.vigencia_hasta = vigencia_hasta
        poliza.save()

        log_poliza_event(
            poliza=poliza,
            tipo=PolizaEvento.Tipo.VIGENCIA_ACTUALIZADA,
            actor=request.user,
            titulo="Vigencia actualizada",
            data={
                "antes": {"desde": str(old_desde), "hasta": str(old_hasta)},
                "despues": {"desde": str(vigencia_desde), "hasta": str(vigencia_hasta)},
            },
        )

    messages.success(request, "Vigencia actualizada.")
    return redirect("ui:poliza_detail", pk=poliza.pk)


@login_required
@require_POST
def poliza_documento_subir(request, pk):
    poliza = get_object_or_404(Poliza, pk=pk)

    # Permisos: Admin/Supervisor siempre; Agente solo su póliza
    if not (can_admin_polizas(request.user) or poliza.agente_id == request.user.id):
        messages.error(request, "No tienes permisos para adjuntar documentos a esta póliza.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    archivo = request.FILES.get("archivo")
    if not archivo:
        messages.error(request, "Selecciona un archivo para subir.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # Validación simple: PDF
    if not (archivo.name.lower().endswith(".pdf") or (archivo.content_type or "").lower() == "application/pdf"):
        messages.error(request, "Solo se permite subir PDF.")
        return redirect("ui:poliza_detail", pk=poliza.pk)

    # Crear Documento y asignarlo a póliza
    with transaction.atomic():
        doc = Documento.objects.create(
            nombre_archivo=(request.POST.get("nombre_archivo") or archivo.name).strip() or archivo.name,
            tipo=Documento.Tipo.PDF,
            file=archivo,
            tamano=getattr(archivo, "size", 0) or 0,
            subido_por=request.user,
        )

        anterior_id = poliza.documento_id
        poliza.documento = doc
        poliza.save(update_fields=["documento", "updated_at"])

        # Bitácora
        log_poliza_event(
            poliza=poliza,
            tipo=PolizaEvento.Tipo.POLIZA_DOCUMENTO_ADJUNTADO,
            actor=request.user,
            titulo="Documento de póliza adjuntado",
            data={
                "documento_id": doc.id,
                "nombre_archivo": doc.nombre_archivo,
                "reemplazo_de": anterior_id,
            },
        )

    messages.success(request, "Documento adjuntado correctamente.")
    return redirect("ui:poliza_detail", pk=poliza.pk)
