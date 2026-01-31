from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from crm.models import Cliente
from cotizador.models import Cotizacion
from autos.models import Vehiculo
from portal.forms_public import CotizacionPublicaForm


from datetime import timedelta
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from crm.models import Cliente
from cotizador.models import Cotizacion
from autos.models import Vehiculo
from portal.forms_public import CotizacionPublicaForm


class PortalCotizarCreateView(View):
    template_name = "portal/cotizar.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CotizacionPublicaForm()})

    def post(self, request):
        form = CotizacionPublicaForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        d = form.cleaned_data

        # ===== Cliente prospecto =====
        cliente, _ = Cliente.objects.get_or_create(
            email_principal=d["email"],
            defaults={
                "tipo_cliente": d["tipo_cliente"],
                "telefono_principal": d["telefono"],
                "estatus": Cliente.Estatus.PROSPECTO,
                "origen": "PORTAL_PUBLICO",
            },
        )

        cliente.telefono_principal = d["telefono"]
        cliente.tipo_cliente = d["tipo_cliente"]
        if cliente.tipo_cliente == Cliente.TipoCliente.PERSONA:
            cliente.nombre = d.get("nombre", "") or cliente.nombre
            cliente.apellido_paterno = d.get("apellido_paterno", "") or cliente.apellido_paterno
            cliente.apellido_materno = d.get("apellido_materno", "") or cliente.apellido_materno
        else:
            cliente.nombre_comercial = d.get("nombre_comercial", "") or cliente.nombre_comercial
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
            vin=d.get("vin", ""),
        )

        # ===== Vigencia automática =====
        hoy = timezone.localdate()
        vigencia_desde = hoy
        vigencia_hasta = hoy + timedelta(days=365)

        # ===== Cotización =====
        cot = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=vigencia_desde,
            vigencia_hasta=vigencia_hasta,
            notas=d.get("notas", ""),
            estatus=Cotizacion.Estatus.BORRADOR,
            origen=Cotizacion.Origen.PORTAL_PUBLICO,
        )

        request.session["cotizacion_publica_id"] = cot.id
        messages.success(request, "¡Listo! Aquí está el resumen de tu solicitud.")
        return redirect("portal:cotizar_resumen")

        # ===== Cotización =====

#        Cotizacion.objects.create(
#            cliente=cliente,
#            vehiculo=vehiculo,
#            flotilla=None,
#            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
#            vigencia_desde=vigencia_desde,
#            vigencia_hasta=vigencia_hasta,
#            notas=d.get("notas", ""),
#            estatus=Cotizacion.Estatus.BORRADOR,
#        )

#        messages.success(request, "¡Listo! Recibimos tu solicitud de cotización. En breve te contactamos.")
#        return redirect("portal:cotizar")
