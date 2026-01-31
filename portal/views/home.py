from django.shortcuts import redirect
from django.views import View


class PortalHomeView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("portal:dashboard")
        return redirect("portal:cotizar")

from django.views.generic import TemplateView

class AccesoSuspendidoView(TemplateView):
    template_name = "portal/acceso_suspendido.html"
