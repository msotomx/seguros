from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class ClientePortalRequiredMixin(LoginRequiredMixin):
    """
    Exige que el usuario tenga un Cliente ligado (user_portal).
    """

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "cliente_portal", None):
            raise PermissionDenied("Este usuario no está ligado a un Cliente para Portal.")
        return super().dispatch(request, *args, **kwargs)

    @property
    def cliente(self):
        return self.request.user.cliente_portal
