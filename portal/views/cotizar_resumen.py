from django.shortcuts import redirect, render
from django.views import View

from cotizador.models import Cotizacion


class PortalCotizarResumenView(View):
    template_name = "portal/cotizar_resumen.html"

    def get(self, request):
        cotizacion_id = request.session.get("cotizacion_publica_id")
        if not cotizacion_id:
            return redirect("portal:cotizar")

        try:
            cotizacion = (
                Cotizacion.objects
                .select_related("cliente", "vehiculo", "vehiculo__catalogo", "vehiculo__catalogo__marca", "vehiculo__catalogo__submarca")
                .get(id=cotizacion_id)
            )
        except Cotizacion.DoesNotExist:
            return redirect("portal:cotizar")

        return render(request, self.template_name, {"cotizacion": cotizacion})
