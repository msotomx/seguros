from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView

from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from crm.models import Cliente
from ui.forms import ClienteQuickCreateForm

# ALTA DE CLIENTE CON LOS CAMPOS MINIMOS REQUERIDOS PARA SEGUIR EL FLUJO AL CREAR UNA COTIZACION EN EL PORTAL
# REDIRIGE A NUEVO VEHICULO
class ClienteQuickCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "crm.add_cliente"
    model = Cliente
    form_class = ClienteQuickCreateForm
    template_name = "ui/crm/cliente_quick_create.html"

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("origen", "UI")
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.estatus = Cliente.Estatus.PROSPECTO

        # Cartera: si no puede reasignar, se asigna a sí mismo
        if not self.request.user.has_perm("crm.reassign_cliente_owner"):
            obj.owner = self.request.user

        obj.save()
        messages.success(self.request, "Cliente creado correctamente.")

        # Se queda seleccionado para el wizard
        self.request.session["wiz_cot_cliente_id"] = obj.id
        return redirect(reverse("ui:cotizacion_new_vehiculo"))

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from crm.models import Cliente
from ui.forms import ClienteForm

class ClienteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Cliente
    template_name = "ui/clientes/cliente_list.html"
    context_object_name = "clientes"
    permission_required = "crm.view_cliente"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True).select_related("owner")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                # búsqueda simple; luego refinamos
                nombre__icontains=q
            ) | qs.filter(apellido_paterno__icontains=q) | qs.filter(rfc__icontains=q) | qs.filter(email_principal__icontains=q)
        return qs.order_by("-id")


# ALTA DE CLIENTE CON TODOS LOS CAMPOS
class ClienteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "crm.add_cliente"
    model = Cliente
    form_class = ClienteForm
    template_name = "ui/clientes/cliente_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("origen", "UI")
        initial.setdefault("estatus", Cliente.Estatus.PROSPECTO)
        initial.setdefault("portal_activo", True)
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)

        # Regla: al crear desde UI, inicia como prospecto si no viene definido
        if not obj.estatus:
            obj.estatus = Cliente.Estatus.PROSPECTO

        # Cartera: si no puede reasignar, se asigna a sí mismo
        if not self.request.user.has_perm("crm.reassign_cliente_owner"):
            obj.owner = self.request.user

        obj.save()
        messages.success(self.request, "Cliente creado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        # Después de crear, manda a detalle
        return reverse_lazy("ui:cliente_detail", kwargs={"pk": self.object.pk})


class ClienteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm              # ✅ usar el form
    template_name = "ui/clientes/cliente_form.html"
    permission_required = "crm.change_cliente"

    def get_success_url(self):
        messages.success(self.request, "Cliente actualizado correctamente.")
        return reverse_lazy("ui:cliente_detail", kwargs={"pk": self.object.pk})

class ClienteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Cliente
    template_name = "ui/clientes/cliente_detail.html"
    context_object_name = "cliente"
    permission_required = "crm.view_cliente"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("owner", "direccion_fiscal", "direccion_contacto", "user_portal")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cliente = self.object

        ctx["stats"] = {
            "cotizaciones": cliente.cotizaciones.count(),
            "vehiculos": cliente.vehiculos.count(),
            "polizas": cliente.polizas.count(),
            "incidentes": cliente.incidentes.count(),
        }
        return ctx


@login_required
@permission_required("crm.manage_portal_activo", raise_exception=True)
@require_POST
def cliente_portal_toggle(request, pk: int):
    """
    Activa / desactiva el acceso al portal para un Cliente.
    - Requiere permiso: crm.manage_portal_activo
    - POST-only
    """
    cliente = get_object_or_404(Cliente, pk=pk, is_active=True)

    cliente.portal_activo = not cliente.portal_activo
    cliente.save(update_fields=["portal_activo"])

    estado = "ACTIVADO" if cliente.portal_activo else "SUSPENDIDO"
    messages.success(request, f"Acceso al portal {estado} para el cliente.")

    # Regresa a la página previa si existe; si no, al dashboard UI
    return redirect(request.META.get("HTTP_REFERER", "ui:dashboard"))
