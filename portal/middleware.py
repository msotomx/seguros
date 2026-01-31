from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout

class PortalActivoMiddleware:
    """
    Bloquea acceso al portal si el cliente tiene portal_activo = False
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo aplica a rutas del portal
        if request.path.startswith("/portal/"):
            user = request.user

            if user.is_authenticated:
                cliente = getattr(user, "cliente_portal", None)

                # Es cliente y tiene portal inactivo
                if cliente and not cliente.portal_activo:
                    logout(request)
                    return redirect("portal:acceso_suspendido")

        return self.get_response(request)
