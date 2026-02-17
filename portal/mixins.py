from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class ClientePortalRequiredMixin(LoginRequiredMixin):

    @property
    def cliente(self):
        return self.request.user.cliente_portal

    def dispatch(self, request, *args, **kwargs):
        # Si no está logueado, LoginRequiredMixin redirige y termina aquí
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Cliente ligado
        try:
            cliente = request.user.cliente_portal
        except Exception:
            messages.error(request, "Tu usuario no está ligado a un cliente del portal.")
            return redirect('accounts/login')

        # Portal activo
        if not cliente.portal_activo:
            messages.error(request, "Tu acceso al portal está deshabilitado.")
            raise PermissionDenied  # o redirect(self.login_url)

        return super().dispatch(request, *args, **kwargs)
