from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.views.generic import ListView, CreateView, DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.timezone import localdate
from datetime import timedelta

from ui.forms import CotizacionDatosForm
from autos.models import Vehiculo
from crm.models import Cliente
from cotizador.models import Cotizacion, CotizacionItem


def _is_admin(user) -> bool:
    return user.is_superuser or user.groups.filter(name="Admin").exists()

class CotizacionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "cotizador.view_cotizacion"
    template_name = "ui/cotizador/cotizacion_list.html"
    context_object_name = "cotizaciones"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Cotizacion.objects
            .select_related("cliente", "vehiculo", "flotilla", "owner")
            .order_by("-created_at")
        )

        user = self.request.user

        # Si NO es admin, por defecto solo su cartera
        if not (user.is_superuser or user.groups.filter(name="Admin").exists()):
            qs = qs.filter(owner=user)

        # Filtros
        estatus = self.request.GET.get("estatus", "").strip()
        if estatus:
            qs = qs.filter(estatus=estatus)

        tipo = self.request.GET.get("tipo", "").strip()
        if tipo:
            qs = qs.filter(tipo_cotizacion=tipo)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(cliente__nombre_comercial__icontains=q) |
                Q(cliente__nombre__icontains=q) |
                Q(cliente__apellido_paterno__icontains=q) |
                Q(cliente__rfc__icontains=q) |
                Q(owner__username__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["estatus_choices"] = Cotizacion.Estatus.choices
        ctx["tipo_choices"] = Cotizacion.Tipo.choices
        ctx["filters"] = {
            "estatus": self.request.GET.get("estatus", ""),
            "tipo": self.request.GET.get("tipo", ""),
            "q": self.request.GET.get("q", ""),
        }
        return ctx


class CotizacionDetailView(DetailView):
    model = Cotizacion
    template_name = "ui/cotizador/cotizacion_detail.html"
    context_object_name = "cotizacion"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Permiso mínimo
        if not request.user.has_perm("cotizador.view_cotizacion"):
            return HttpResponseForbidden("No tienes permiso para ver cotizaciones.")

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user

        # Regla de cartera: si no es Admin/superuser, solo puede ver sus cotizaciones
        is_admin = user.is_superuser or user.groups.filter(name="Admin").exists()
        if not is_admin and obj.owner_id != user.id:
            raise PermissionError("No autorizado para ver esta cotización.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        items = (
            CotizacionItem.objects
            .filter(cotizacion=self.object)
            .select_related("aseguradora", "producto")
            .order_by("-seleccionada", "ranking", "prima_total")
        )

        ctx["items"] = items
        ctx["selected_item"] = items.filter(seleccionada=True).first()
        ctx["can_select"] = (
            self.request.user.has_perm("cotizador.change_cotizacionitem")
            and self.object.estatus == Cotizacion.Estatus.BORRADOR
        )
        ctx["can_change_status"] = self.request.user.has_perm("cotizador.change_cotizacion")
        ctx["ya_emitida"] = Poliza.objects.filter(cotizacion_item__cotizacion=self.object).exists()
        ctx["can_calcular"] = (
            self.request.user.has_perm("cotizador.change_cotizacion")
            and self.object.estatus in [Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA]
        )
        ctx["can_emitir"] = (
            ctx["selected_item"] is not None
            and self.request.user.has_perm("polizas.add_poliza")
            and self.object.estatus in [Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA]
        )

        return ctx


class CotizacionItemDetailView(LoginRequiredMixin, DetailView):
    model = CotizacionItem
    template_name = "ui/cotizador/cotizacion_item_detail.html"
    context_object_name = "item"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("cotizador.view_cotizacionitem"):
            return HttpResponseForbidden("No tienes permiso para ver items de cotización.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)

        # Cartera: si no es admin, debe ser owner de la cotización
        if not _is_admin(self.request.user):
            if obj.cotizacion.owner_id != self.request.user.id:
                raise PermissionError("No autorizado para ver este item.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Si existe trazabilidad del motor:
        ctx["calculo"] = getattr(self.object, "calculo", None)

        # Listas - Coberturas/reglas (si existen) (pueden estar vacías)
        ctx["coberturas"] = self.object.coberturas.select_related("cobertura").all()
        ctx["reglas"] = self.object.reglas_aplicadas.select_related("regla").order_by("orden")

        return ctx


@login_required
@permission_required("cotizador.change_cotizacionitem", raise_exception=True)
def cotizacion_select_item(request, pk: int, item_id: int):
    """
    Marca un item como seleccionado y desmarca los demás.
    """
    cotizacion = get_object_or_404(Cotizacion, pk=pk)

    # Regla de cartera
    is_admin = request.user.is_superuser or request.user.groups.filter(name="Admin").exists()
    if not is_admin and cotizacion.owner_id != request.user.id:
        return HttpResponseForbidden("No autorizado para modificar esta cotización.")

    item = get_object_or_404(CotizacionItem, pk=item_id, cotizacion=cotizacion)

    with transaction.atomic():
        CotizacionItem.objects.filter(cotizacion=cotizacion, seleccionada=True).exclude(pk=item.pk).update(seleccionada=False)
        CotizacionItem.objects.filter(pk=item.pk).update(seleccionada=True)

    messages.success(request, f"Seleccionaste: {item.aseguradora.nombre} - {item.producto.nombre_producto}")
    return redirect(reverse("ui:cotizacion_detail", kwargs={"pk": cotizacion.pk}))

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView
from crm.models import Cliente


class CotizacionWizardClienteSelectView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Wizard - Paso 1: buscar/seleccionar cliente.
    Guarda cliente_id en session y manda al paso 2.
    """
    permission_required = "crm.view_cliente"
    template_name = "ui/cotizador/wizard_cliente_select.html"
    context_object_name = "clientes"
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        qs = Cliente.objects.filter(is_active=True).order_by("-updated_at")

        # Cartera: si NO puede reasignar, solo ve sus clientes
        if not user.has_perm("crm.reassign_cliente_owner"):
            qs = qs.filter(owner=user)

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(nombre_comercial__icontains=q) |
                Q(nombre__icontains=q) |
                Q(apellido_paterno__icontains=q) |
                Q(apellido_materno__icontains=q) |
                Q(rfc__icontains=q) |
                Q(email_principal__icontains=q) |
                Q(telefono_principal__icontains=q)
            )

        return qs

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("cotizador.add_cotizacion"):
            messages.error(request, "No tienes permiso para crear cotizaciones.")
            return redirect(reverse("ui:cotizacion_new_cliente"))

        cliente_id = request.POST.get("cliente_id")
        if not cliente_id:
            messages.error(request, "Selecciona un cliente.")
            return redirect(reverse("ui:cotizacion_new_cliente"))

        request.session["wiz_cot_cliente_id"] = int(cliente_id)
        messages.success(request, "Cliente seleccionado. Continuemos con vehículo/flotilla.")
        #return redirect(reverse("ui:cotizacion_new_vehiculo"))
        return redirect(reverse("ui:cotizacion_new_tipo"))
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["can_create_cliente"] = self.request.user.has_perm("crm.add_cliente")
        return ctx

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from crm.models import Cliente


class CotizacionWizardTipoView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "cotizador.add_cotizacion"
    template_name = "ui/cotizador/wizard_tipo.html"

    def dispatch(self, request, *args, **kwargs):
        # Debe existir cliente seleccionado
        cliente_id = request.session.get("wiz_cot_cliente_id")
        if not cliente_id:
            messages.warning(request, "Primero selecciona un cliente.")
            return redirect(reverse("ui:cotizacion_new_cliente"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        tipo = request.POST.get("tipo")
        if tipo not in ("INDIVIDUAL", "FLOTILLA"):
            messages.error(request, "Selecciona el tipo de cotización.")
            return redirect(reverse("ui:cotizacion_new_tipo"))

        request.session["wiz_cot_tipo"] = tipo

        if tipo == "INDIVIDUAL":
            return redirect(reverse("ui:cotizacion_new_vehiculo"))

        # Flotilla (más adelante)
        messages.info(request, "Flotilla se implementará en el siguiente paso.")
        return redirect(reverse("ui:cotizacion_new_tipo"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente_id = self.request.session.get("wiz_cot_cliente_id")
        ctx["cliente"] = Cliente.objects.filter(id=cliente_id).first()
        return ctx

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from crm.models import Cliente
from autos.models import Vehiculo, VehiculoCatalogo
from ui.forms import VehiculoFromCatalogoForm


class CotizacionWizardVehiculoSelectView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "cotizador.add_cotizacion"
    template_name = "ui/cotizador/wizard_vehiculo_select.html"

    def dispatch(self, request, *args, **kwargs):
        cliente_id = request.session.get("wiz_cot_cliente_id")
        tipo = request.session.get("wiz_cot_tipo")

        if not cliente_id:
            messages.warning(request, "Primero selecciona un cliente.")
            return redirect(reverse("ui:cotizacion_new_cliente"))

        if tipo != "INDIVIDUAL":
            messages.warning(request, "Primero selecciona tipo de cotización (Individual).")
            return redirect(reverse("ui:cotizacion_new_tipo"))

        return super().dispatch(request, *args, **kwargs)

    def _cliente(self):
        cliente_id = self.request.session.get("wiz_cot_cliente_id")
        return Cliente.objects.get(id=cliente_id)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        # A) Seleccionar vehículo existente del cliente
        if action == "select_vehiculo":
            vehiculo_id = request.POST.get("vehiculo_id")
            if not vehiculo_id:
                messages.error(request, "Selecciona un vehículo.")
                return redirect(reverse("ui:cotizacion_new_vehiculo"))

            request.session["wiz_cot_vehiculo_id"] = int(vehiculo_id)
            messages.success(request, "Vehículo seleccionado. Continuemos con datos de cotización.")
            return redirect(reverse("ui:cotizacion_new_datos"))

        # B) Crear vehículo del cliente desde catálogo global
        if action == "create_from_catalogo":
            if not request.user.has_perm("autos.add_vehiculo"):
                messages.error(request, "No tienes permiso para crear vehículos.")
                return redirect(reverse("ui:cotizacion_new_vehiculo"))

            form = VehiculoFromCatalogoForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Revisa los datos para crear el vehículo.")
                return redirect(reverse("ui:cotizacion_new_vehiculo") + "?tab=catalogo&q=" + (request.GET.get("q") or ""))

            cliente = self._cliente()
            #catalogo = VehiculoCatalogo.objects.get(id=form.cleaned_data["catalogo_id"])
            catalogo = form.cleaned_data["catalogo_id"]   # catalogo_id es el objeto


            v = Vehiculo.objects.create(
                cliente=cliente,
                catalogo=catalogo,
                tipo_uso=form.cleaned_data["tipo_uso"],
                # Texto auxiliar (útil aunque tengas FK a catálogo)
                marca_texto=catalogo.marca.nombre,
                submarca_texto=catalogo.submarca.nombre,
                modelo_anio=catalogo.anio,
                version=catalogo.version or "",
                tipo_vehiculo=catalogo.tipo_vehiculo or "",
                placas=(form.cleaned_data.get("placas") or "").strip(),
                vin=(form.cleaned_data.get("vin") or "").strip(),
                color=(form.cleaned_data.get("color") or "").strip(),
                valor_comercial=form.cleaned_data.get("valor_comercial"),
            )

            request.session["wiz_cot_vehiculo_id"] = v.id
            messages.success(request, "Vehículo creado y seleccionado. Continuemos con datos de cotización.")
            return redirect(reverse("ui:cotizacion_new_datos"))

        messages.error(request, "Acción no válida.")
        return redirect(reverse("ui:cotizacion_new_vehiculo"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self._cliente()

        tab = (self.request.GET.get("tab") or "mis").strip()
        q = (self.request.GET.get("q") or "").strip()

        # Mis vehículos (del cliente)
        mis_qs = Vehiculo.objects.filter(cliente=cliente, is_active=True).select_related("catalogo", "catalogo__marca", "catalogo__submarca")
        if q and tab == "mis":
            mis_qs = mis_qs.filter(
                Q(placas__icontains=q) |
                Q(vin__icontains=q) |
                Q(marca_texto__icontains=q) |
                Q(submarca_texto__icontains=q) |
                Q(modelo_anio__icontains=q)
            )
        mis_qs = mis_qs.order_by("-updated_at")[:30]

        # Catálogo global
        cat_qs = VehiculoCatalogo.objects.filter(is_active=True).select_related("marca", "submarca")
        if q and tab == "catalogo":
            cat_qs = cat_qs.filter(
                Q(marca__nombre__icontains=q) |
                Q(submarca__nombre__icontains=q) |
                Q(anio__icontains=q) |
                Q(version__icontains=q) |
                Q(clave_amis__icontains=q)
            )
        cat_qs = cat_qs.order_by("-updated_at")[:30]

        ctx.update({
            "cliente": cliente,
            "tab": tab,
            "q": q,
            "mis_vehiculos": mis_qs,
            "catalogo_vehiculos": cat_qs,
            "can_create_vehiculo": self.request.user.has_perm("autos.add_vehiculo"),
            "tipo_uso_choices": Vehiculo.TipoUso.choices,
        })
        return ctx

# CALCULAR COTIZACIONES
from decimal import Decimal
from itertools import product

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
    CotizacionItemCalculo,
    CotizacionItemCobertura,
    CotizacionItemReglaAplicada,
)

from catalogos.models import Aseguradora, ProductoSeguro
from tarifas.services.rating_engine import RatingEngine

@require_POST
@login_required
@permission_required("cotizador.change_cotizacion", raise_exception=True)
def cotizacion_calcular(request, pk: int):
    """
    Genera opciones (CotizacionItem) usando el motor real.
    Guarda trazabilidad en CotizacionItemCalculo.
    """
    cot = get_object_or_404(Cotizacion, pk=pk)

    # Regla de estatus para recalcular (ajústala a tu gusto)
    if cot.estatus not in [Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA]:
        messages.warning(request, "Esta cotización ya no se puede recalcular.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # Regla de cartera: si no es Admin, sólo owner puede recalcular
    user = request.user
    is_admin = user.is_superuser or user.groups.filter(name="Admin").exists()
    if not is_admin and cot.owner_id != user.id:
        messages.error(request, "No autorizado para recalcular esta cotización.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    engine = RatingEngine()

    try:
        results = engine.quote(cot)  # <- debe regresar lista de [QuoteResult]
    except Exception as e:
        messages.error(request, f"No se pudo calcular con el motor de tarifas: {e}")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # si el motor no regresa opciones
    if not results:
        messages.error(
            request,
            "No se pudieron generar opciones de cotización. "
            "Verifica que existan aseguradoras y productos activos en los catálogos."
        )
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    with transaction.atomic():
        # Recalcular desde cero: limpia items previos y selección
        cot.items.all().delete()

        seen = set()  # para evitar duplicados (aseguradora_id, producto_id)

        for r in results:
            key = (int(r.aseguradora_id), int(r.producto_id))
            if key in seen:
                continue
            seen.add(key)

            item = CotizacionItem.objects.create(
                cotizacion=cot,
                aseguradora_id=r.aseguradora_id,
                producto_id=r.producto_id,
                prima_neta=r.prima_neta,
                derechos=r.derechos,
                recargos=r.recargos,
                descuentos=r.descuentos,
                iva=r.iva,
                prima_total=r.prima_total,
                forma_pago=r.forma_pago or "",
                meses=r.meses,
                observaciones="",
                ranking=r.ranking or 0,
                seleccionada=False,
            )

            # --- trazabilidad (siempre que venga del motor) ---
            # Si tu engine no lo manda, estos campos quedan default.
            if getattr(r, "detalle_json", None) is not None:
                CotizacionItemCalculo.objects.update_or_create(
                    item=item,
                    defaults={
                        "prima_base": getattr(r, "prima_base", Decimal("0.00")) or Decimal("0.00"),
                        "factor_total": getattr(r, "factor_total", Decimal("1.000000")) or Decimal("1.000000"),
                        "detalle_json": r.detalle_json or {},
                    },
                )

            # --- (opcional) coberturas ---
            # Si tu engine llena r.coberturas = [{"cobertura_id":.., "incluida":.., "valor":.., "notas":..}, ...]
            coberturas = getattr(r, "coberturas", None) or []
            for c in coberturas:
                # espera cobertura_id (FK a CoberturaCatalogo)
                CovId = c.get("cobertura_id")
                if not CovId:
                    continue
                CotizacionItemCobertura.objects.update_or_create(
                    item=item,
                    cobertura_id=CovId,
                    defaults={
                        "incluida": bool(c.get("incluida", True)),
                        "valor": (c.get("valor") or "")[:120],
                        "notas": (c.get("notas") or ""),
                    },
                )

            # --- (opcional) reglas aplicadas ---
            # Si tu engine llena r.reglas = [{"regla_id":.., "resultado":.., "valor_resultante":.., "mensaje":.., "orden":..}, ...]
            reglas = getattr(r, "reglas", None) or []
            for rr in reglas:
                regla_id = rr.get("regla_id")
                if not regla_id:
                    continue
                CotizacionItemReglaAplicada.objects.create(
                    item=item,
                    regla_id=regla_id,
                    resultado=rr.get("resultado") or CotizacionItemReglaAplicada.Resultado.APLICO,
                    valor_resultante=(rr.get("valor_resultante") or "")[:200],
                    mensaje=(rr.get("mensaje") or ""),
                    orden=int(rr.get("orden") or 1),
                )

    messages.success(request, "Opciones calculadas correctamente.")
    return redirect("ui:cotizacion_detail", pk=cot.pk)

@login_required
@permission_required("cotizador.change_cotizacion", raise_exception=True)
@require_POST
@transaction.atomic
def cotizacion_calcular2(request, pk: int):
    """
    Genera opciones (CotizacionItem) para una cotización.
    - Preferente: motor real tarifas (RatingEngine)
    - Fallback: stub robusto (combos únicos)
    """
    cot = get_object_or_404(Cotizacion, pk=pk)

    if not _is_admin(request.user) and cot.owner_id != request.user.id:
        return HttpResponseForbidden("No autorizado para recalcular esta cotización.")

    if cot.estatus not in [Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA]:
        messages.warning(request, "Esta cotización ya no se puede recalcular.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # Limpia items previos (cascade borra coberturas/calculo/reglas)
    cot.items.all().delete()

    # 1) Intentar motor real
    try:
        engine = RatingEngine()
        results = engine.quote(cot)  # debe regresar lista de QuoteResult
    except NotImplementedError:
        results = None
    except Exception as e:
        # si el motor falla, mostramos error y caemos a stub si quieres
        messages.warning(request, f"Motor de tarifas no disponible ({e}). Usando modo demo.")
        results = None

    # si los catalogos estan vacios, no hace nada
    if not results:
        messages.error(
            request,
            "No se pudieron generar opciones de cotización. "
            "Verifica que existan aseguradoras y productos activos en los catálogos."
        )
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    if results:
        created = 0
        for i, r in enumerate(results, start=1):
            item = CotizacionItem.objects.create(
                cotizacion=cot,
                aseguradora_id=r.aseguradora_id,
                producto_id=r.producto_id,
                prima_neta=r.prima_neta,
                derechos=r.derechos,
                recargos=r.recargos,
                descuentos=r.descuentos,
                iva=r.iva,
                prima_total=r.prima_total,
                forma_pago=r.forma_pago or "",
                meses=r.meses,
                observaciones="",
                ranking=r.ranking or i,
                seleccionada=False,
            )

            # cálculo (trazabilidad)
            CotizacionItemCalculo.objects.create(
                item=item,
                prima_base=getattr(r, "prima_base", Decimal("0.00")),
                factor_total=getattr(r, "factor_total", Decimal("1.0")),
                detalle_json=getattr(r, "detalle_json", None) or {},
            )

            # coberturas
            for c in (getattr(r, "coberturas", None) or []):
                CotizacionItemCobertura.objects.create(
                    item=item,
                    cobertura_id=c["cobertura_id"],
                    incluida=c.get("incluida", True),
                    valor=c.get("valor", ""),
                    notas=c.get("notas", ""),
                )

            # reglas aplicadas
            for idx, rr in enumerate((getattr(r, "reglas", None) or []), start=1):
                CotizacionItemReglaAplicada.objects.create(
                    item=item,
                    regla_id=rr["regla_id"],
                    resultado=rr["resultado"],
                    valor_resultante=rr.get("valor_resultante", ""),
                    mensaje=rr.get("mensaje", ""),
                    orden=idx,
                )

            created += 1

        messages.success(request, f"Opciones generadas por motor: {created}.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # 2) Fallback STUB robusto (combos únicos)
    aseguradoras = list(Aseguradora.objects.all()[:10])
    productos = list(ProductoSeguro.objects.all()[:10])

    if not aseguradoras or not productos:
        messages.error(request, "No hay aseguradoras/productos en catálogos para generar opciones.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    combos = list(product(aseguradoras, productos))
    max_items = 3
    to_create = combos[:max_items]

    base = Decimal("8500.00")
    for i, (aseg, prod) in enumerate(to_create, start=1):
        CotizacionItem.objects.create(
            cotizacion=cot,
            aseguradora=aseg,
            producto=prod,
            prima_neta=base + Decimal(i - 1) * Decimal("900.00"),
            derechos=Decimal("450.00"),
            recargos=Decimal("0.00"),
            descuentos=Decimal("0.00"),
            iva=Decimal("0.00"),
            prima_total=(base + Decimal(i - 1) * Decimal("900.00")) + Decimal("450.00"),
            forma_pago="CONTADO",
            ranking=i,
        )

    messages.success(request, f"Opciones generadas (modo demo): {len(to_create)}.")
    return redirect("ui:cotizacion_detail", pk=cot.pk)

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from cotizador.models import Cotizacion, CotizacionItem
from polizas.models import Poliza
from polizas.services import generar_numero_poliza

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.db import transaction

from polizas.models import Poliza
from polizas.models import PolizaEvento
from polizas.services import log_poliza_event


@require_POST
@login_required
@permission_required("polizas.add_poliza", raise_exception=True)
def cotizacion_emitir_poliza(request, pk: int):
    cot = get_object_or_404(Cotizacion, pk=pk)

    # cartera
    user = request.user
    is_admin = user.is_superuser or user.groups.filter(name="Admin").exists()
    if not is_admin and cot.owner_id != user.id:
        messages.error(request, "No autorizado para emitir póliza de esta cotización.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # estado
    if cot.estatus not in [Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA, Cotizacion.Estatus.ACEPTADA]:
        messages.warning(request, "Esta cotización no permite emisión.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    selected_item = cot.items.filter(seleccionada=True).select_related("aseguradora", "producto").first()
    if not selected_item:
        messages.error(request, "Primero selecciona una opción para emitir póliza.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # Evitar doble emisión: si ya existe póliza vinculada a este item
    existente = Poliza.objects.filter(cotizacion_item=selected_item).first()
    if existente:
        messages.info(request, "Ya existe una póliza creada para esta opción.")
        # si luego haces PolizaDetailView, aquí redirigimos allí
        return redirect("ui:poliza_list")

    with transaction.atomic():
        # número de póliza: placeholder (hasta integrar emisión real con aseguradora)
        numero = f"TEMP-{selected_item.cotizacion.folio}"

        poliza = Poliza.objects.create(
            cliente=cot.cliente,
            vehiculo=cot.vehiculo,
            flotilla=cot.flotilla,
            aseguradora=selected_item.aseguradora,
            producto=selected_item.producto,
            cotizacion_item=selected_item,
            numero_poliza=numero,
            fecha_emision = None, # hasta que se emita la poliza se asigna fecha
            vigencia_desde=cot.vigencia_desde,
            vigencia_hasta=cot.vigencia_hasta,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_total=selected_item.prima_total,
            forma_pago=selected_item.forma_pago or cot.forma_pago_preferida or "",
            agente=cot.owner,
        )

        # Marcar la cotización como ACEPTADA (por el cliente)
        cot.estatus = Cotizacion.Estatus.ACEPTADA
        cot.save(update_fields=["estatus"])

    log_poliza_event(
        poliza=poliza,
        tipo=PolizaEvento.Tipo.CREADA,
        actor=request.user,
        titulo="Póliza creada desde cotización",
        data={
            "cotizacion_folio": cot.folio,
            "cotizacion_id": cot.id,
            "cotizacion_item_id": selected_item.id,
            "vigencia_desde": str(poliza.vigencia_desde),
            "vigencia_hasta": str(poliza.vigencia_hasta),
            "prima_total": str(poliza.prima_total),
        },
    )

    messages.success(request, f"Póliza creada en proceso: {poliza.numero_poliza}")
    return redirect("ui:poliza_list")

@login_required
@permission_required("polizas.add_poliza", raise_exception=True)
@require_POST
@transaction.atomic
def cotizacion_emitir(request, pk: int):
    cot = get_object_or_404(Cotizacion, pk=pk)

    # Regla de cartera (igual que tu DetailView)
    if not _is_admin(request.user) and cot.owner_id != request.user.id:
        return HttpResponseForbidden("No autorizado para emitir pólizas de esta cotización.")

    # Debe existir item seleccionado
    item = (
        CotizacionItem.objects
        .select_related("aseguradora", "producto", "cotizacion")
        .filter(cotizacion=cot, seleccionada=True)
        .first()
    )
    if not item:
        messages.error(request, "Primero selecciona una opción para poder emitir.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    if Poliza.objects.filter(cotizacion_item=item).exists():
        messages.warning(request, "Esta opción ya fue emitida como póliza.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # (Opcional) solo permitir emisión en ciertos estados
    if cot.estatus not in [Cotizacion.Estatus.BORRADOR, Cotizacion.Estatus.ENVIADA, Cotizacion.Estatus.ACEPTADA]:
        messages.warning(request, "Esta cotización no está en un estado válido para emitir.")
        return redirect("ui:cotizacion_detail", pk=cot.pk)

    # Genera número único por aseguradora (cumple uq_poliza_por_aseguradora)
    numero = generar_numero_poliza(item.aseguradora_id)

    # Respeta el CheckConstraint: vehiculo XOR flotilla
    vehiculo = cot.vehiculo if cot.tipo_cotizacion == Cotizacion.Tipo.INDIVIDUAL else None
    flotilla = cot.flotilla if cot.tipo_cotizacion == Cotizacion.Tipo.FLOTILLA else None

    poliza = Poliza.objects.create(
        cliente=cot.cliente,
        vehiculo=vehiculo,
        flotilla=flotilla,
        aseguradora=item.aseguradora,
        producto=item.producto,
        cotizacion_item=item,
        numero_poliza=numero,
        vigencia_desde=cot.vigencia_desde,
        vigencia_hasta=cot.vigencia_hasta,
        estatus=Poliza.Estatus.EN_PROCESO,
        prima_total=item.prima_total,
        forma_pago=item.forma_pago or cot.forma_pago_preferida or "",
        agente=cot.owner or request.user,
        # documento=None (cuando adjuntes PDF/XML de póliza)
    )

    # Marca cotización como aceptada (o “convertida” si luego agregas ese estatus)
    if cot.estatus != Cotizacion.Estatus.ACEPTADA:
        cot.estatus = Cotizacion.Estatus.ACEPTADA
        cot.save(update_fields=["estatus"])

    messages.success(request, f"Póliza creada: {poliza.numero_poliza}")
    #return redirect("ui:poliza_detail", pk=poliza.pk) ***
    return redirect("ui:poliza_list")

# Crea Cotizacion en ui
class CotizacionWizardDatosView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "cotizador.add_cotizacion"
    model = Cotizacion
    form_class = CotizacionDatosForm
    template_name = "ui/cotizador/wizard_cotizacion_nueva.html"

    def dispatch(self, request, *args, **kwargs):
        # Validar que existan pasos previos en sesión
        cliente_id = request.session.get("wiz_cot_cliente_id")
        tipo = request.session.get("wiz_cot_tipo")
        vehiculo_id = request.session.get("wiz_cot_vehiculo_id")

        if not cliente_id:
            messages.warning(request, "Primero selecciona un cliente.")
            return redirect(reverse("ui:cotizacion_new_cliente"))

        if tipo != "INDIVIDUAL":
            messages.warning(request, "Primero selecciona tipo de cotización (Individual).")
            return redirect(reverse("ui:cotizacion_new_tipo"))

        if not vehiculo_id:
            messages.warning(request, "Primero selecciona o crea un vehículo.")
            return redirect(reverse("ui:cotizacion_new_vehiculo"))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        print("INITIAL:", self.get_initial())
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(CotizacionDatosForm.initial_defaults())
        return initial

    def form_valid(self, form):
        cliente = Cliente.objects.get(id=self.request.session["wiz_cot_cliente_id"])
        vehiculo = Vehiculo.objects.get(id=self.request.session["wiz_cot_vehiculo_id"])

        cot = form.save(commit=False)
        cot.cliente = cliente
        cot.vehiculo = vehiculo
        cot.flotilla = None
        cot.tipo_cotizacion = Cotizacion.Tipo.INDIVIDUAL
        cot.origen = Cotizacion.Origen.AGENTE  # o "CRM" según tu criterio
        cot.estatus = Cotizacion.Estatus.BORRADOR

        # Cartera
        cot.owner = self.request.user
        cot.created_by = self.request.user
        today = localdate()
        cot.vigencia_desde = today
        cot.vigencia_hasta = today + timedelta(days=365)
        
        cot.save()

        # Limpia el wizard (opcional, recomendado)
        for k in ["wiz_cot_cliente_id", "wiz_cot_tipo", "wiz_cot_vehiculo_id"]:
            self.request.session.pop(k, None)

        messages.success(self.request, f"Cotización creada: {cot.folio}")
        return redirect("ui:cotizacion_detail", pk=cot.pk)


@property
def esta_vigente(self):
    from django.utils.timezone import now
    hoy = localdate()
    return self.estatus == self.Estatus.VIGENTE and self.vigencia_desde <= hoy <= self.vigencia_hasta


@property
def dias_restantes(self):
    from django.utils.timezone import now
    if not self.vigencia_hasta:
        return None
    return (self.vigencia_hasta - localdate()).days
