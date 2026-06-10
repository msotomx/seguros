from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View

from ui.forms import UsuarioCreateForm, UsuarioUpdateForm

User = get_user_model()


class UsuarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = "ui/usuarios/usuario_list.html"
    context_object_name = "usuarios"
    paginate_by = 25
    permission_required = "accounts.change_userprofile"

    def get_queryset(self):
        qs = User.objects.select_related("perfil").order_by("first_name", "last_name", "username")

        q = self.request.GET.get("q", "").strip()
        rol = self.request.GET.get("rol", "").strip()

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(username__icontains=q) |
                Q(email__icontains=q)
            )

        if rol:
            qs = qs.filter(perfil__rol=rol)

        return qs


class UsuarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = User
    form_class = UsuarioCreateForm
    template_name = "ui/usuarios/usuario_form.html"
    success_url = reverse_lazy("ui:usuario_list")
    permission_required = "accounts.add_userprofile"

    def form_valid(self, form):
        messages.success(self.request, "Usuario creado correctamente.")
        return super().form_valid(form)


class UsuarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = User
    form_class = UsuarioUpdateForm
    template_name = "ui/usuarios/usuario_form.html"
    success_url = reverse_lazy("ui:usuario_list")
    permission_required = "accounts.change_userprofile"

    def form_valid(self, form):
        messages.success(self.request, "Usuario actualizado correctamente.")
        return super().form_valid(form)


class UsuarioToggleActivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "accounts.change_userprofile"

    def post(self, request, pk):
        user = User.objects.get(pk=pk)

        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        messages.success(request, "Estatus del usuario actualizado.")
        return redirect("ui:usuario_list")
    

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.urls import reverse_lazy

from accounts.forms import BootstrapPasswordChangeForm


class CambiarPasswordView(LoginRequiredMixin, PasswordChangeView):
    form_class = BootstrapPasswordChangeForm
    template_name = "ui/usuarios/password_change_form.html"
    success_url = reverse_lazy("ui:mi_password_change_done")


class CambiarPasswordDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "ui/usuarios/password_change_done.html"
