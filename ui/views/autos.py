from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from autos.models import Marca, SubMarca, VehiculoCatalogo, Vehiculo
from ui.forms import MarcaForm, SubMarcaForm, VehiculoCatalogoForm, VehiculoForm


class MarcaListView(LoginRequiredMixin, ListView):
    model = Marca
    template_name = "ui/autos/marca_list.html"
    context_object_name = "marcas"
    paginate_by = 25

    def get_queryset(self):
        qs = Marca.objects.filter(is_active=True).order_by("nombre")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs


class MarcaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Marca
    form_class = MarcaForm
    template_name = "ui/autos/marca_form.html"
    success_url = reverse_lazy("ui:marca_list")
    permission_required = "autos.manage_vehiculos"


class MarcaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Marca
    form_class = MarcaForm
    template_name = "ui/autos/marca_form.html"
    success_url = reverse_lazy("ui:marca_list")
    permission_required = "autos.manage_vehiculos"


class SubMarcaListView(LoginRequiredMixin, ListView):
    model = SubMarca
    template_name = "ui/autos/submarca_list.html"
    context_object_name = "submarcas"
    paginate_by = 25

    def get_queryset(self):
        qs = SubMarca.objects.select_related("marca").filter(is_active=True).order_by("marca__nombre", "nombre")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(marca__nombre__icontains=q))
        return qs


class SubMarcaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SubMarca
    form_class = SubMarcaForm
    template_name = "ui/autos/submarca_form.html"
    success_url = reverse_lazy("ui:submarca_list")
    permission_required = "autos.manage_vehiculos"


class SubMarcaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SubMarca
    form_class = SubMarcaForm
    template_name = "ui/autos/submarca_form.html"
    success_url = reverse_lazy("ui:submarca_list")
    permission_required = "autos.manage_vehiculos"


class VehiculoCatalogoListView(LoginRequiredMixin, ListView):
    model = VehiculoCatalogo
    template_name = "ui/autos/vehiculo_catalogo_list.html"
    context_object_name = "vehiculos_catalogo"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            VehiculoCatalogo.objects
            .select_related("marca", "submarca")
            .filter(is_active=True)
            .order_by("marca__nombre", "submarca__nombre", "-anio", "version")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(marca__nombre__icontains=q) |
                Q(submarca__nombre__icontains=q) |
                Q(version__icontains=q) |
                Q(clave_amis__icontains=q) |
                Q(tipo_vehiculo__icontains=q)
            )
        return qs


class VehiculoCatalogoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = VehiculoCatalogo
    form_class = VehiculoCatalogoForm
    template_name = "ui/autos/vehiculo_catalogo_form.html"
    success_url = reverse_lazy("ui:vehiculo_catalogo_list")
    permission_required = "autos.manage_vehiculos"


class VehiculoCatalogoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = VehiculoCatalogo
    form_class = VehiculoCatalogoForm
    template_name = "ui/autos/vehiculo_catalogo_form.html"
    success_url = reverse_lazy("ui:vehiculo_catalogo_list")
    permission_required = "autos.manage_vehiculos"


class VehiculoListView(LoginRequiredMixin, ListView):
    model = Vehiculo
    template_name = "ui/autos/vehiculo_list.html"
    context_object_name = "vehiculos"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Vehiculo.objects
            .select_related("cliente", "catalogo", "catalogo__marca", "catalogo__submarca")
            .filter(is_active=True)
            .order_by("-id")
        )

        user = self.request.user
        if not user.has_perm("accounts.view_reportes"):
            qs = qs.filter(cliente__owner=user)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(cliente__nombre__icontains=q) |
                Q(marca_texto__icontains=q) |
                Q(submarca_texto__icontains=q) |
                Q(version__icontains=q) |
                Q(vin__icontains=q) |
                Q(placas__icontains=q)
            )
        return qs


class VehiculoCreateView(LoginRequiredMixin, CreateView):
    model = Vehiculo
    form_class = VehiculoForm
    template_name = "ui/autos/vehiculo_form.html"
    success_url = reverse_lazy("ui:vehiculo_list")


class VehiculoUpdateView(LoginRequiredMixin, UpdateView):
    model = Vehiculo
    form_class = VehiculoForm
    template_name = "ui/autos/vehiculo_form.html"
    success_url = reverse_lazy("ui:vehiculo_list")

    def get_queryset(self):
        qs = Vehiculo.objects.filter(is_active=True)
        user = self.request.user
        if not user.has_perm("accounts.view_reportes"):
            qs = qs.filter(cliente__owner=user)
        return qs

