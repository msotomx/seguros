from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from crm.models import Cliente
from crm.models import CodigoPostal
from cotizador.models import Cotizacion
from autos.models import Vehiculo
from portal.forms_public import CotizacionPublicaForm

from datetime import timedelta
from django.contrib import messages
from django.utils import timezone

from tarifas.services.rating_engine import RatingEngine
from cotizador.models import CotizacionItem, CotizacionItemCalculo 


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
                }
            )

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        d = form.cleaned_data

        # ===== Cliente prospecto =====
        cliente = (
            Cliente.objects
            .filter(email_principal=d["email"])
            .order_by("-id")
            .first()
        )

        if not cliente:
            cliente = Cliente.objects.create(
                email_principal=d["email"],
                tipo_cliente=d["tipo_cliente"],
                telefono_principal=d["telefono"],
                estatus=Cliente.Estatus.PROSPECTO,
                origen="PORTAL_PUBLICO",
                codigo_postal=d["codigo_postal"],
            )
        cliente.codigo_postal = d["codigo_postal"]
        cp = CodigoPostal.objects.filter(codigo_postal=d["codigo_postal"]).first()

        if cp:
            cliente.ciudad = cp.ciudad
            cliente.estado = cp.estado
        else:
            cliente.ciudad = ""
            cliente.estado = ""

        cliente.telefono_principal = d["telefono"]
        cliente.tipo_cliente = d["tipo_cliente"]
        if cliente.tipo_cliente == Cliente.TipoCliente.PERSONA:
            cliente.nombre = d.get("nombre", "") or cliente.nombre
            cliente.apellido_paterno = d.get("apellido_paterno", "") or cliente.apellido_paterno
            cliente.apellido_materno = d.get("apellido_materno", "") or cliente.apellido_materno
        else:
            cliente.nombre_comercial = d.get("nombre_comercial", "") or cliente.nombre_comercial
        cliente.codigo_postal = d["codigo_postal"]
        cliente.save()

        # ===== Vehículo desde catálogo =====
        vc = d["catalogo"]  # VehiculoCatalogo seleccionado

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            catalogo=vc,
            tipo_uso=d["tipo_uso"],
            marca_texto=vc.marca.nombre,
            submarca_texto=vc.submarca.nombre,
            modelo_anio=vc.anio,
            version=vc.version or "",
            tipo_vehiculo=vc.tipo_vehiculo or "",
            valor_comercial=vc.valor_referencia,  # si quieres usarlo
            placas=d.get("placas", ""),
            vin = (d.get("vin") or "").strip().upper(),
        )

        # ===== Vigencia automática =====
        hoy = timezone.localdate()
        vigencia_desde = hoy
        vigencia_hasta = hoy + timedelta(days=365)

        # ===== Cotización =====
        cot = Cotizacion.objects.create(
            cliente=cliente,
            codigo_postal=d.get("codigo_postal", ""),
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=vigencia_desde,
            vigencia_hasta=vigencia_hasta,
            notas=d.get("notas", ""),
            estatus=Cotizacion.Estatus.BORRADOR,
            origen=Cotizacion.Origen.PORTAL_PUBLICO,
            ciudad = Cliente.ciudad,
            estado = Cliente.estado,
        )
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

        request.session["cotizacion_publica_id"] = cot.id
        messages.success(request, "¡Listo! Aquí está el resumen de tu solicitud.")
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
