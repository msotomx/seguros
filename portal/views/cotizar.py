from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from autos.models import Vehiculo

from crm.models import Cliente, CodigoPostal
from portal.forms_public import CotizacionPublicaForm
from cotizador.models import Cotizacion
from cotizador.services.portal_multi_provider_quote_service import (
    PortalMultiProviderQuoteService,
)


class PortalCotizarCreateView(View):
    template_name = "portal/cotizar.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CotizacionPublicaForm()})

    def post(self, request):
        form = CotizacionPublicaForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "show_step_2": True,
                },
            )

        d = form.cleaned_data

        # =====================================================
        # Cliente prospecto
        # =====================================================

        cliente = (
            Cliente.objects
            .filter(email_principal=d["email"])
            .order_by("-id")
            .first()
        )

        if not cliente:
            cliente = Cliente.objects.create(
                tipo_cliente=Cliente.TipoCliente.PERSONA,
                nombre=d["nombre"],
                email_principal=d["email"],
                telefono_principal=d["telefono"],
                estatus=Cliente.Estatus.PROSPECTO,
                origen=Cotizacion.Origen.PORTAL_PUBLICO,
                codigo_postal=d["codigo_postal"],
            )

        # Actualizamos los datos de contacto capturados.
        cliente.nombre = d["nombre"]
        cliente.email_principal = d["email"]
        cliente.telefono_principal = d["telefono"]
        cliente.tipo_cliente = Cliente.TipoCliente.PERSONA
        cliente.codigo_postal = d["codigo_postal"]
        cliente.genero = d["genero"]

        cp = (
            CodigoPostal.objects
            .filter(
                codigo_postal=d["codigo_postal"]
            )
            .first()
        )

        if cp:
            cliente.ciudad = cp.ciudad
            cliente.estado = cp.estado
        else:
            cliente.ciudad = ""
            cliente.estado = ""

        cliente.save()

        # =====================================================
        # Vehículo
        # =====================================================

        catalogo = d["catalogo"]

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            catalogo=catalogo,

            # El modelo tiene PARTICULAR como default.
            # Lo indicamos explícitamente porque es una regla
            # del flujo público actual.
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,

            marca_texto=catalogo.marca.nombre,
            submarca_texto=catalogo.submarca.nombre,
            modelo_anio=catalogo.anio,
            version=catalogo.version or "",
            tipo_vehiculo=catalogo.tipo_vehiculo or "",
            valor_comercial=catalogo.valor_referencia,
        )

        # =====================================================
        # Vigencia
        # =====================================================

        hoy = timezone.localdate()

        vigencia_desde = hoy
        vigencia_hasta = hoy + timedelta(days=365)

        # =====================================================
        # Cotización
        # =====================================================

        cot = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,

            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,

            vigencia_desde=vigencia_desde,
            vigencia_hasta=vigencia_hasta,

            estatus=Cotizacion.Estatus.BORRADOR,
            origen=Cotizacion.Origen.PORTAL_PUBLICO,

            codigo_postal=d["codigo_postal"],
            ciudad=cliente.ciudad,
            estado=cliente.estado,

            conductor_nombre=d["nombre"],
            conductor_genero=d["genero"],
            conductor_edad=d["edad"],
        )

        # =====================================================
        # Motor de tarifas
        # =====================================================

        items = PortalMultiProviderQuoteService.quote(
            cotizacion=cot,
            ambiente="SIT",
            ramo="AUTOS",
        )

        if not items:
            has_provider_errors = (
                cot.resultados_proveedor
                .filter(success=False)
                .exists()
            )

            if has_provider_errors:
                messages.warning(
                    request,
                    (
                        "No fue posible obtener cotizaciones "
                        "de una o más aseguradoras. "
                        "Intenta nuevamente más tarde."
                    ),
                )
            else:
                messages.warning(
                    request,
                    (
                        "No encontramos opciones disponibles "
                        "para los datos capturados."
                    ),
                )

        # =====================================================
        # Sesión pública
        # =====================================================

        request.session["cotizacion_publica_id"] = cot.id

        messages.success(
            request,
            "¡Listo! Aquí está el resumen de tu solicitud.",
        )

        return redirect(
            "portal:cotizacion_opciones",
            pk=cot.pk,
        )


from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, View

from cotizador.models import Cotizacion, CotizacionItem

# VISTA PARA MOSTRAR OPCIONES DE COTIZACIONES EN EL PORTAL
class PortalCotizacionOpcionesView(DetailView):
    model = Cotizacion
    template_name = "portal/cotizacion_opciones.html"
    context_object_name = "cotizacion"

    def get_queryset(self):
        return Cotizacion.objects.select_related("cliente", "vehiculo")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["items"] = (
            CotizacionItem.objects
            .filter(cotizacion=self.object)
            .select_related("aseguradora", "producto")
            .order_by("ranking", "prima_total")
        )

        return ctx

from django.contrib import messages
from django.db import transaction

# VISTA PARA SELECCIONAR OPCION

class PortalSeleccionarCotizacionItemView(View):

    @transaction.atomic
    def post(self, request, pk, item_id):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)

        item = get_object_or_404(
            CotizacionItem,
            pk=item_id,
            cotizacion=cotizacion,
        )

        CotizacionItem.objects.filter(cotizacion=cotizacion).update(
            seleccionada=False
        )

        item.seleccionada = True
        item.save(update_fields=["seleccionada"])

        cotizacion.estatus = Cotizacion.Estatus.ACEPTADA
        cotizacion.save(update_fields=["estatus"])

        messages.success(request, "Opción seleccionada correctamente.")
        return redirect("portal:cotizacion_gracias", pk=cotizacion.pk)


class PortalCotizacionGraciasView(DetailView):
    model = Cotizacion
    template_name = "portal/cotizacion_gracias.html"
    context_object_name = "cotizacion"
