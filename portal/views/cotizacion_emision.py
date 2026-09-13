from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views import View

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
)
from portal.forms_emision import (
    CotizacionConductorForm,
    CotizacionDireccionForm,
    CotizacionVehiculoForm,    
)
from crm.models import Direccion


class PublicCotizacionSessionMixin:
    """
    Protege el flujo público verificando que la Cotizacion
    corresponda a la almacenada en sesión.
    """

    def get_cotizacion(self, request, pk):
        cotizacion_id = request.session.get(
            "cotizacion_publica_id"
        )

        if not cotizacion_id:
            return None

        if int(cotizacion_id) != int(pk):
            return None

        return (
            Cotizacion.objects
            .select_related(
                "cliente",
                "vehiculo",
            )
            .filter(pk=pk)
            .first()
        )


class PortalSeleccionarCotizacionItemView(
    PublicCotizacionSessionMixin,
    View,
):
    @transaction.atomic
    def post(
        self,
        request,
        pk,
        item_id,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        item = get_object_or_404(
            CotizacionItem,
            pk=item_id,
            cotizacion=cotizacion,
            provider_option__isnull=False,
        )

        CotizacionItem.objects.filter(
            cotizacion=cotizacion,
        ).update(
            seleccionada=False
        )

        item.seleccionada = True
        item.save(
            update_fields=[
                "seleccionada",
            ]
        )

        cotizacion.estatus = (
            Cotizacion.Estatus.ACEPTADA
        )

        cotizacion.save(
            update_fields=[
                "estatus",
                "updated_at",
            ]
        )

        request.session[
            "cotizacion_item_seleccionado_id"
        ] = item.id

        return redirect(
            "portal:cotizacion_conductor",
            pk=cotizacion.pk,
        )


class PortalCotizacionConductorView(
    PublicCotizacionSessionMixin,
    View,
):
    template_name = (
        "portal/cotizacion_conductor.html"
    )

    def get(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        if not self._selected_item_exists(
            request,
            cotizacion,
        ):
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        cliente = cotizacion.cliente

        form = CotizacionConductorForm(
            initial={
                "nombre": (
                    cotizacion.conductor_nombre
                    or cliente.nombre
                ),
                "apellido_paterno": (
                    cotizacion
                    .conductor_apellido_paterno
                    or cliente.apellido_paterno
                ),
                "apellido_materno": (
                    cotizacion
                    .conductor_apellido_materno
                    or cliente.apellido_materno
                ),
                "rfc": (
                    cotizacion.conductor_rfc
                    or cliente.rfc
                ),
                "curp": cliente.curp,
                "fecha_nacimiento": (
                    cotizacion
                    .conductor_fecha_nacimiento
                ),
            }
        )

        return render(
            request,
            self.template_name,
            {
                "cotizacion": cotizacion,
                "form": form,
            },
        )

    @transaction.atomic
    def post(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        if not self._selected_item_exists(
            request,
            cotizacion,
        ):
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        form = CotizacionConductorForm(
            request.POST
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "cotizacion": cotizacion,
                    "form": form,
                },
            )

        data = form.cleaned_data

        cotizacion.conductor_nombre = (
            data["nombre"]
        )
        cotizacion.conductor_apellido_paterno = (
            data["apellido_paterno"]
        )
        cotizacion.conductor_apellido_materno = (
            data["apellido_materno"]
        )
        cotizacion.conductor_rfc = (
            data["rfc"]
        )

        cotizacion.conductor_fecha_nacimiento = (
            data["fecha_nacimiento"]
        )

        cotizacion.save(
            update_fields=[
                "conductor_nombre",
                "conductor_apellido_paterno",
                "conductor_apellido_materno",
                "conductor_rfc",
                "conductor_fecha_nacimiento",
                "updated_at",
            ]
        )

        cliente = cotizacion.cliente

        cliente.nombre = data["nombre"]
        cliente.apellido_paterno = (
            data["apellido_paterno"]
        )
        cliente.apellido_materno = (
            data["apellido_materno"]
        )
        cliente.rfc = data["rfc"]
        cliente.curp = data["curp"]
        
        cliente.save(
            update_fields=[
                "nombre",
                "apellido_paterno",
                "apellido_materno",
                "rfc",
                "curp",
                "updated_at",
            ]
        )

        return redirect(
            "portal:cotizacion_direccion",
            pk=cotizacion.pk,
        )

    @staticmethod
    def _selected_item_exists(
        request,
        cotizacion,
    ):
        item_id = request.session.get(
            "cotizacion_item_seleccionado_id"
        )

        if not item_id:
            return False

        return CotizacionItem.objects.filter(
            pk=item_id,
            cotizacion=cotizacion,
            seleccionada=True,
            provider_option__isnull=False,
        ).exists()


class PortalCotizacionDireccionView(
    PublicCotizacionSessionMixin,
    View,
):
    template_name = (
        "portal/cotizacion_direccion.html"
    )

    def get(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        if not self._selected_item_exists(
            request,
            cotizacion,
        ):
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        direccion = (
            cotizacion.cliente.direccion_contacto
        )

        initial = {}

        if direccion is not None:
            initial = {
                "calle": direccion.calle,
                "num_ext": direccion.num_ext,
                "colonia": direccion.colonia,
            }

        form = CotizacionDireccionForm(
            codigo_postal=cotizacion.codigo_postal,
            initial=initial,
        )

        return render(
            request,
            self.template_name,
            {
                "cotizacion": cotizacion,
                "form": form,
            },
        )

    @transaction.atomic
    def post(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        if not self._selected_item_exists(
            request,
            cotizacion,
        ):
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        form = CotizacionDireccionForm(
            request.POST,
            codigo_postal=cotizacion.codigo_postal,
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "cotizacion": cotizacion,
                    "form": form,
                },
            )

        data = form.cleaned_data
        cliente = cotizacion.cliente

        direccion = cliente.direccion_contacto

        if direccion is None:
            direccion = Direccion()

        direccion.calle = data["calle"]
        direccion.num_ext = data["num_ext"]
        direccion.colonia = data["colonia"]
        direccion.ciudad = cotizacion.ciudad
        direccion.estado = cotizacion.estado
        direccion.cp = cotizacion.codigo_postal
        direccion.pais = "México"

        direccion.save()

        if (
            cliente.direccion_contacto_id
            != direccion.id
        ):
            cliente.direccion_contacto = direccion

            cliente.save(
                update_fields=[
                    "direccion_contacto",
                    "updated_at",
                ]
            )

        return redirect(
            "portal:cotizacion_vehiculo",
            pk=cotizacion.pk,
        )

    @staticmethod
    def _selected_item_exists(
        request,
        cotizacion,
    ):
        item_id = request.session.get(
            "cotizacion_item_seleccionado_id"
        )

        if not item_id:
            return False

        return CotizacionItem.objects.filter(
            pk=item_id,
            cotizacion=cotizacion,
            seleccionada=True,
            provider_option__isnull=False,
        ).exists()

class PortalCotizacionVehiculoView(
    PublicCotizacionSessionMixin,
    View,
):
    template_name = (
        "portal/cotizacion_vehiculo.html"
    )

    def get(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        if not self._selected_item_exists(
            request,
            cotizacion,
        ):
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        vehiculo = cotizacion.vehiculo

        form = CotizacionVehiculoForm(
            initial={
                "placas": vehiculo.placas,
                "vin": vehiculo.vin,
            }
        )

        return render(
            request,
            self.template_name,
            {
                "cotizacion": cotizacion,
                "vehiculo": vehiculo,
                "form": form,
            },
        )

    @transaction.atomic
    def post(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        if not self._selected_item_exists(
            request,
            cotizacion,
        ):
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        form = CotizacionVehiculoForm(
            request.POST
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "cotizacion": cotizacion,
                    "vehiculo": cotizacion.vehiculo,
                    "form": form,
                },
            )

        data = form.cleaned_data

        vehiculo = cotizacion.vehiculo

        vehiculo.placas = data["placas"]
        vehiculo.vin = data["vin"]

        vehiculo.save(
            update_fields=[
                "placas",
                "vin",
                "updated_at",
            ]
        )

        return redirect(
            "portal:cotizacion_resumen_emision",
            pk=cotizacion.pk,
        )

    @staticmethod
    def _selected_item_exists(
        request,
        cotizacion,
    ):
        item_id = request.session.get(
            "cotizacion_item_seleccionado_id"
        )

        if not item_id:
            return False

        return CotizacionItem.objects.filter(
            pk=item_id,
            cotizacion=cotizacion,
            seleccionada=True,
            provider_option__isnull=False,
        ).exists()

class PortalCotizacionResumenEmisionView(
    PublicCotizacionSessionMixin,
    View,
):
    template_name = (
        "portal/cotizacion_resumen_emision.html"
    )

    def get(
        self,
        request,
        pk,
    ):
        cotizacion = self.get_cotizacion(
            request,
            pk,
        )

        if cotizacion is None:
            return redirect(
                "portal:cotizar"
            )

        item = self._get_selected_item(
            request,
            cotizacion,
        )

        if item is None:
            return redirect(
                "portal:cotizacion_opciones",
                pk=cotizacion.pk,
            )

        cliente = cotizacion.cliente
        vehiculo = cotizacion.vehiculo

        if (
            cliente.direccion_contacto_id is None
        ):
            return redirect(
                "portal:cotizacion_direccion",
                pk=cotizacion.pk,
            )

        if (
            not vehiculo.placas.strip()
            or not vehiculo.vin.strip()
        ):
            return redirect(
                "portal:cotizacion_vehiculo",
                pk=cotizacion.pk,
            )

        if (
            not cotizacion.conductor_apellido_paterno
            or not cotizacion.conductor_rfc
            or cotizacion.conductor_fecha_nacimiento
            is None
        ):
            return redirect(
                "portal:cotizacion_conductor",
                pk=cotizacion.pk,
            )

        return render(
            request,
            self.template_name,
            {
                "cotizacion": cotizacion,
                "item": item,
                "cliente": cliente,
                "direccion": (
                    cliente.direccion_contacto
                ),
                "vehiculo": vehiculo,
                "opcion": item.provider_option,
            },
        )

    @staticmethod
    def _get_selected_item(
        request,
        cotizacion,
    ):
        item_id = request.session.get(
            "cotizacion_item_seleccionado_id"
        )

        if not item_id:
            return None

        return (
            CotizacionItem.objects
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
            .filter(
                pk=item_id,
                cotizacion=cotizacion,
                seleccionada=True,
                provider_option__isnull=False,
            )
            .first()
        )
