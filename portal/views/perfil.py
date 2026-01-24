from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView

from portal.mixins import ClientePortalRequiredMixin
from portal.forms import PortalClientePerfilForm


class PortalPerfilView(ClientePortalRequiredMixin, UpdateView):
    template_name = "portal/perfil_form.html"
    form_class = PortalClientePerfilForm
    success_url = reverse_lazy("portal:dashboard")

    def get_object(self, queryset=None):
        return self.cliente  # solo puede editar su propio registro

    def form_valid(self, form):
        messages.success(self.request, "Tus datos se guardaron correctamente.")
        return super().form_valid(form)
