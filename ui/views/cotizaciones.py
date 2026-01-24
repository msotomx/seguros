from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from cotizador.models import Cotizacion


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


from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from cotizador.models import Cotizacion, CotizacionItem

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
        ctx["can_select"] = self.request.user.has_perm("cotizador.change_cotizacionitem")
        ctx["can_change_status"] = self.request.user.has_perm("cotizador.change_cotizacion")
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
            catalogo = VehiculoCatalogo.objects.get(id=form.cleaned_data["catalogo_id"])

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
