from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView

from crm.models import Cliente
from ui.forms import ClienteQuickCreateForm

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
