from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from autos.models import Vehiculo
from cotizador.models import (
    Cotizacion,
    CotizacionItem,
    CotizacionItemCalculo,
)
from crm.models import Cliente, CodigoPostal
from portal.forms_public import CotizacionPublicaForm
from tarifas.services.rating_engine import RatingEngine


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
        # Motor actual de tarifas
        #
        # Por ahora lo conservamos.
        # En el siguiente paso será reemplazado/encapsulado
        # por el nuevo QuoteService.
        # =====================================================

        engine = RatingEngine()

        results = engine.quote(cot)

        for r in results:
            item = CotizacionItem.objects.create(
                cotizacion=cot,
                aseguradora_id=r.aseguradora_id,
                producto_id=r.producto_id,

                prima_neta=r.prima_neta,
                derechos=r.derechos,
                recargos=r.recargos,
                descuentos=r.descuentos,
                iva=r.iva,
                prima_total=r.prima_total,

                forma_pago=r.forma_pago,
                meses=r.meses,
                ranking=r.ranking,
                seleccionada=False,
            )

            CotizacionItemCalculo.objects.create(
                item=item,
                prima_base=r.prima_base,
                factor_total=r.factor_total,
                detalle_json=r.detalle_json or {},
            )

        # =====================================================
        # Sesión pública
        # =====================================================

        request.session["cotizacion_publica_id"] = cot.id

        messages.success(
            request,
            "¡Listo! Aquí está el resumen de tu solicitud.",
        )

        return redirect("portal:cotizar_resumen")


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
