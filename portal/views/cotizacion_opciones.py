from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.views.generic import DetailView
from django.views import View

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
)


class PortalCotizacionOpcionesView(DetailView):
    """
    Muestra las opciones comerciales generadas por
    proveedores externos para una cotización pública.
    """

    model = Cotizacion
    template_name = "portal/cotizacion_opciones.html"
    context_object_name = "cotizacion"

    def dispatch(self, request, *args, **kwargs):
        cotizacion_id = request.session.get(
            "cotizacion_publica_id"
        )

        if not cotizacion_id:
            return redirect("portal:cotizar")

        if int(cotizacion_id) != int(kwargs["pk"]):
            return redirect("portal:cotizar")

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_queryset(self):
        return (
            Cotizacion.objects
            .select_related(
                "cliente",
                "vehiculo",
                "vehiculo__catalogo",
                "vehiculo__catalogo__marca",
                "vehiculo__catalogo__submarca",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )

        items = (
            CotizacionItem.objects
            .filter(
                cotizacion=self.object,
                provider_option__isnull=False,
            )
            .select_related(
                "aseguradora",
                "producto",
                "provider_option",
                "provider_option__riesgo",
                (
                    "provider_option__"
                    "cotizacion_proveedor"
                ),
            )
            .prefetch_related(
                "provider_option__coberturas",
            )
            .order_by(
                "ranking",
                "prima_total",
                "id",
            )
        )

        context["items"] = items

        return context
    