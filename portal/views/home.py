from django.shortcuts import redirect
from django.views import View


from django.views.generic import TemplateView

class AccesoSuspendidoView(TemplateView):
    template_name = "portal/acceso_suspendido.html"
