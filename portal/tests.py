from django.test import TestCase
from datetime import date
from portal.forms_public import CotizacionPublicaForm

from unittest.mock import patch

from django.urls import reverse

from autos.models import (
    Marca,
    SubMarca,
    Vehiculo,
    VehiculoCatalogo,
)
from crm.models import Cliente, CodigoPostal
from catalogos.models import (
    Aseguradora,
    ProductoSeguro,
)

from cotizador.models import (
    Cotizacion,
    CotizacionItem,
    CotizacionProveedor,
    CotizacionProveedorCobertura,
    CotizacionProveedorOpcion,
    CotizacionProveedorRiesgo,
)
from crm.models import (
    Cliente,
    CodigoPostal,
    Direccion,
)
from portal.forms_emision import CotizacionVehiculoForm

class CotizacionPublicaFormTests(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(
            nombre="Nissan",
            is_active=True,
        )

        self.submarca = SubMarca.objects.create(
            marca=self.marca,
            nombre="Versa",
            is_active=True,
        )

        self.catalogo = VehiculoCatalogo.objects.create(
            marca=self.marca,
            submarca=self.submarca,
            anio=2024,
            version="Advance CVT",
            is_active=True,
        )

        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Centro",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

    def _valid_data(self):
        return {
            "nombre": "Miguel",
            "genero": "MASCULINO",
            "email": "miguel@example.com",
            "telefono": "6561234567",
            "edad": 45,
            "codigo_postal": "32500",
            "marca": self.marca.pk,
            "submarca": self.submarca.pk,
            "modelo_anio": "2024",
            "catalogo": self.catalogo.pk,
            "acepta_aviso_privacidad": "on",
        }

    def test_formulario_valido(self):
        form = CotizacionPublicaForm(
            data=self._valid_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_nombre_es_obligatorio(self):
        data = self._valid_data()
        data["nombre"] = ""

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)

    def test_genero_es_obligatorio(self):
        data = self._valid_data()
        data["genero"] = ""

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("genero", form.errors)

    def test_edad_es_obligatoria(self):
        data = self._valid_data()
        data["edad"] = ""

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("edad", form.errors)

    def test_codigo_postal_debe_tener_cinco_digitos(self):
        data = self._valid_data()
        data["codigo_postal"] = "3250"

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("codigo_postal", form.errors)

    def test_codigo_postal_debe_ser_numerico(self):
        data = self._valid_data()
        data["codigo_postal"] = "32A00"

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("codigo_postal", form.errors)

    def test_codigo_postal_debe_existir(self):
        data = self._valid_data()
        data["codigo_postal"] = "99999"

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("codigo_postal", form.errors)

    def test_version_debe_corresponder_a_marca_submarca_y_anio(self):
        otra_marca = Marca.objects.create(
            nombre="Volkswagen",
            is_active=True,
        )

        otra_submarca = SubMarca.objects.create(
            marca=otra_marca,
            nombre="Jetta",
            is_active=True,
        )

        otro_catalogo = VehiculoCatalogo.objects.create(
            marca=otra_marca,
            submarca=otra_submarca,
            anio=2024,
            version="Comfortline",
            is_active=True,
        )

        data = self._valid_data()

        # Manipulamos el queryset después de construir el formulario
        # para comprobar también la validación semántica.
        form = CotizacionPublicaForm(data=data)

        form.fields["catalogo"].queryset = (
            VehiculoCatalogo.objects.filter(
                pk=otro_catalogo.pk
            )
        )

        data["catalogo"] = otro_catalogo.pk

        form = CotizacionPublicaForm(data=data)
        form.fields["catalogo"].queryset = (
            VehiculoCatalogo.objects.all()
        )

        self.assertFalse(form.is_valid())
        self.assertIn("catalogo", form.errors)

    def test_aviso_privacidad_es_obligatorio(self):
        data = self._valid_data()
        data.pop("acepta_aviso_privacidad")

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn(
            "acepta_aviso_privacidad",
            form.errors,
        )


    def test_aviso_privacidad_rechaza_valor_no_marcado(self):
        data = self._valid_data()
        data["acepta_aviso_privacidad"] = ""

        form = CotizacionPublicaForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn(
            "acepta_aviso_privacidad",
            form.errors,
        )


    def test_aviso_privacidad_aceptado_es_valido(self):
        data = self._valid_data()
        data["acepta_aviso_privacidad"] = "on"

        form = CotizacionPublicaForm(data=data)

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertTrue(
            form.cleaned_data[
                "acepta_aviso_privacidad"
            ]
        )

class PortalCotizarCreateViewTests(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(
            nombre="Nissan",
            is_active=True,
        )

        self.submarca = SubMarca.objects.create(
            marca=self.marca,
            nombre="Versa",
            is_active=True,
        )

        self.catalogo = VehiculoCatalogo.objects.create(
            marca=self.marca,
            submarca=self.submarca,
            anio=2024,
            version="Advance CVT",
            clave_amis="TEST-001",
            tipo_vehiculo="AUTOMOVIL",
            valor_referencia="350000.00",
            is_active=True,
        )

        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Centro",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

    def _post_data(self):
        return {
            "nombre": "Miguel",
            "genero": Cotizacion.GeneroConductor.MASCULINO,
            "email": "miguel@example.com",
            "telefono": "6561234567",
            "edad": "45",
            "codigo_postal": "32500",

            "marca": str(self.marca.pk),
            "submarca": str(self.submarca.pk),
            "modelo_anio": "2024",
            "catalogo": str(self.catalogo.pk),
            "acepta_aviso_privacidad": "on",
        }

    @patch(
        "portal.views.cotizar."
        "PortalMultiProviderQuoteService.quote"
    )
    def test_post_crea_cliente_vehiculo_y_cotizacion(
        self,
        mock_quote,
    ):
        mock_quote.return_value = ()

        response = self.client.post(
            reverse("portal:cotizar"),
            data=self._post_data(),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        # =================================================
        # Cliente
        # =================================================

        cliente = Cliente.objects.get(
            email_principal="miguel@example.com",
        )

        self.assertEqual(
            cliente.tipo_cliente,
            Cliente.TipoCliente.PERSONA,
        )

        self.assertEqual(
            cliente.nombre,
            "Miguel",
        )

        self.assertEqual(
            cliente.telefono_principal,
            "6561234567",
        )

        self.assertEqual(
            cliente.codigo_postal,
            "32500",
        )

        self.assertEqual(
            cliente.ciudad,
            "Ciudad Juarez",
        )

        self.assertEqual(
            cliente.estado,
            "Chihuahua",
        )

        self.assertEqual(
            cliente.genero,
            Cliente.Genero.MASCULINO,
        )

        # =================================================
        # Vehículo
        # =================================================

        vehiculo = Vehiculo.objects.get(
            cliente=cliente,
        )

        self.assertEqual(
            vehiculo.catalogo,
            self.catalogo,
        )

        self.assertEqual(
            vehiculo.marca_texto,
            "Nissan",
        )

        self.assertEqual(
            vehiculo.submarca_texto,
            "Versa",
        )

        self.assertEqual(
            vehiculo.modelo_anio,
            2024,
        )

        self.assertEqual(
            vehiculo.version,
            "Advance CVT",
        )

        self.assertEqual(
            vehiculo.tipo_uso,
            Vehiculo.TipoUso.PARTICULAR,
        )

        self.assertEqual(
            vehiculo.vin,
            "",
        )

        self.assertEqual(
            vehiculo.placas,
            "",
        )

        # =================================================
        # Cotización
        # =================================================

        cotizacion = Cotizacion.objects.get(
            cliente=cliente,
            vehiculo=vehiculo,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_opciones",
                kwargs={
                    "pk": cotizacion.pk,
                },
            ),
        )

        mock_quote.assert_called_once_with(
            cotizacion=cotizacion,
            ambiente="SIT",
            ramo="AUTOS",
        )

        self.assertEqual(
            self.client.session[
                "cotizacion_publica_id"
            ],
            cotizacion.id,
        )

        self.assertEqual(
            cotizacion.tipo_cotizacion,
            Cotizacion.Tipo.INDIVIDUAL,
        )

class PortalCotizacionOpcionesViewTests(TestCase):

    def setUp(self):
        self.marca = Marca.objects.create(
            nombre="Nissan",
            is_active=True,
        )

        self.submarca = SubMarca.objects.create(
            marca=self.marca,
            nombre="Versa",
            is_active=True,
        )

        self.catalogo = VehiculoCatalogo.objects.create(
            marca=self.marca,
            submarca=self.submarca,
            anio=2024,
            version="Advance CVT",
            clave_amis="TEST-001",
            tipo_vehiculo="AUTOMOVIL",
            valor_referencia="350000.00",
            is_active=True,
        )

        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
            telefono_principal="6561234567",
            codigo_postal="32500",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            catalogo=self.catalogo,
            tipo_uso=Vehiculo.TipoUso.PARTICULAR,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
            version="Advance CVT",
        )

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=date(2026, 8, 24),
            vigencia_hasta=date(2027, 8, 24),
            estatus=Cotizacion.Estatus.BORRADOR,
            origen=Cotizacion.Origen.PORTAL_PUBLICO,
            codigo_postal="32500",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
            conductor_nombre="Miguel",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=45,
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="CHUBB TEST",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Chubb Auto Test",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.resultado = CotizacionProveedor.objects.create(
            cotizacion=self.cotizacion,
            provider_code="CHUBB",
            success=True,
            provider_quote_id="QUOTE-123",
            provider_quote_version_id="VERSION-456",
            currency="MXN",
            total_premium="20398.28",
        )

        self.riesgo = CotizacionProveedorRiesgo.objects.create(
            cotizacion_proveedor=self.resultado,
            provider_risk_id="RISK-789",
            risk_number=1,
            vehicle_key="VEHICLE-001",
        )

        self.opcion = CotizacionProveedorOpcion.objects.create(
            cotizacion_proveedor=self.resultado,
            riesgo=self.riesgo,
            code="1",
            provider_package_id="1",
            name="AMPLIA",
            total_premium="20398.28",
            currency="MXN",
            selected=True,
        )

        CotizacionProveedorCobertura.objects.create(
            opcion=self.opcion,
            code="1",
            name="DAÑOS MATERIALES",
            insured_amount="314358.00",
            deductible="7.00",
            premium="12141.55",
        )

        CotizacionProveedorCobertura.objects.create(
            opcion=self.opcion,
            code="2",
            name="ROBO TOTAL",
            insured_amount="314358.00",
            deductible="9.00",
            premium="528.28",
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            provider_option=self.opcion,
            prima_total="20398.28",
            ranking=1,
            provider="CHUBB",
            provider_quote_id="QUOTE-123",
            paquete_nombre="AMPLIA",
        )

        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Centro",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

        CodigoPostal.objects.create(
            codigo_postal="32500",
            colonia="Partido Romero",
            municipio="Juarez",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
        )

    def _set_public_session(self):
        session = self.client.session
        session["cotizacion_publica_id"] = (
            self.cotizacion.id
        )
        session.save()

    def test_muestra_opcion_con_coberturas(self):
        self._set_public_session()

        response = self.client.get(
            reverse(
                "portal:cotizacion_opciones",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "portal/cotizacion_opciones.html",
        )

        self.assertContains(
            response,
            "AMPLIA",
        )

        self.assertContains(
            response,
            "20398.28",
        )

        self.assertContains(
            response,
            "DAÑOS MATERIALES",
        )

        self.assertContains(
            response,
            "ROBO TOTAL",
        )

        self.assertContains(
            response,
            "314358.00",
        )

    def test_rechaza_cotizacion_que_no_corresponde_a_sesion(
        self,
    ):
        response = self.client.get(
            reverse(
                "portal:cotizacion_opciones",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("portal:cotizar"),
        )

    def test_contexto_solo_incluye_items_con_provider_option(
        self,
    ):
        CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            prima_total="9999.00",
            ranking=2,
            provider="",
            paquete_nombre="LEGACY",
        )

        self._set_public_session()

        response = self.client.get(
            reverse(
                "portal:cotizacion_opciones",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        items = tuple(
            response.context["items"]
        )

        self.assertEqual(
            items,
            (
                self.item,
            ),
        )

    def test_seleccionar_opcion_marca_item_y_redirige_a_conductor(
        self,
    ):
        self._set_public_session()

        response = self.client.post(
            reverse(
                "portal:cotizacion_seleccionar_item",
                kwargs={
                    "pk": self.cotizacion.pk,
                    "item_id": self.item.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_conductor",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
        )

        self.item.refresh_from_db()
        self.cotizacion.refresh_from_db()

        self.assertTrue(
            self.item.seleccionada
        )

        self.assertEqual(
            self.cotizacion.estatus,
            Cotizacion.Estatus.ACEPTADA,
        )

        self.assertEqual(
            self.client.session[
                "cotizacion_item_seleccionado_id"
            ],
            self.item.id,
        )

    def test_conductor_get_requiere_opcion_seleccionada(
        self,
    ):
        self._set_public_session()

        response = self.client.get(
            reverse(
                "portal:cotizacion_conductor",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_opciones",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
        )

    def test_conductor_get_muestra_formulario_despues_de_seleccionar(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.get(
            reverse(
                "portal:cotizacion_conductor",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "portal/cotizacion_conductor.html",
        )

        self.assertContains(
            response,
            "Datos del conductor",
        )

    def test_conductor_post_guarda_datos_y_redirige_a_direccion(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.post(
            reverse(
                "portal:cotizacion_conductor",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
            data={
                "nombre": "Miguel",
                "apellido_paterno": "Soto",
                "apellido_materno": "Lopez",
                "rfc": "SOLM800101ABC",
                "curp": "SOLM800101HCHXXX00",
                "fecha_nacimiento": "1980-01-01",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_direccion",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
        )

        self.cotizacion.refresh_from_db()
        self.cliente.refresh_from_db()

        self.assertEqual(
            self.cotizacion.conductor_apellido_paterno,
            "Soto",
        )

        self.assertEqual(
            self.cotizacion.conductor_apellido_materno,
            "Lopez",
        )

        self.assertEqual(
            self.cotizacion.conductor_rfc,
            "SOLM800101ABC",
        )

        self.assertEqual(
            self.cliente.apellido_paterno,
            "Soto",
        )

        self.assertEqual(
            self.cliente.rfc,
            "SOLM800101ABC",
        )

        self.assertEqual(
            self.cliente.curp,
            "SOLM800101HCHXXX00",
        )

    def test_direccion_post_guarda_direccion_contacto(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.post(
            reverse(
                "portal:cotizacion_direccion",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
            data={
                "calle": "Av. Tecnologico",
                "num_ext": "1234",
                "colonia": "Centro",
            },
        )

        # Todavía falta crear Paso 5.
        # De momento comprobamos que el POST llegó
        # hasta intentar el siguiente redirect.

    def test_vehiculo_get_muestra_datos_despues_de_seleccionar(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.get(
            reverse(
                "portal:cotizacion_vehiculo",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "portal/cotizacion_vehiculo.html",
        )

        self.assertContains(
            response,
            "Nissan",
        )

        self.assertContains(
            response,
            "Versa",
        )

        self.assertContains(
            response,
            "Advance CVT",
        )

    def test_vehiculo_get_requiere_opcion_seleccionada(
        self,
    ):
        self._set_public_session()

        response = self.client.get(
            reverse(
                "portal:cotizacion_vehiculo",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_opciones",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
        )

    def test_direccion_post_guarda_direccion_contacto(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.post(
            reverse(
                "portal:cotizacion_direccion",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
            data={
                "calle": "Av. Tecnologico",
                "num_ext": "1234",
                "colonia": "Centro",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_vehiculo",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
        )

        self.cliente.refresh_from_db()

        self.assertIsNotNone(
            self.cliente.direccion_contacto
        )

        direccion = (
            self.cliente.direccion_contacto
        )

        self.assertEqual(
            direccion.calle,
            "Av. Tecnologico",
        )

        self.assertEqual(
            direccion.num_ext,
            "1234",
        )

        self.assertEqual(
            direccion.colonia,
            "Centro",
        )

        self.assertEqual(
            direccion.cp,
            "32500",
        )

        self.assertEqual(
            direccion.ciudad,
            "Ciudad Juarez",
        )

        self.assertEqual(
            direccion.estado,
            "Chihuahua",
        )

    def test_vehiculo_post_guarda_placas_vin_y_redirige_a_resumen(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.post(
            reverse(
                "portal:cotizacion_vehiculo",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
            data={
                "placas": "ABC123",
                "vin": "1HGBH41JXMN109186",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "portal:cotizacion_resumen_emision",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
        )

        self.vehiculo.refresh_from_db()

        self.assertEqual(
            self.vehiculo.placas,
            "ABC123",
        )

        self.assertEqual(
            self.vehiculo.vin,
            "1HGBH41JXMN109186",
        )

    def test_resumen_emision_muestra_datos_y_coberturas(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        self.cotizacion.conductor_apellido_paterno = "Soto"
        self.cotizacion.conductor_apellido_materno = "Lopez"
        self.cotizacion.conductor_rfc = "SOLM800101ABC"
        self.cotizacion.conductor_fecha_nacimiento = date(
            1980,
            1,
            1,
        )
        self.cotizacion.save()

        direccion = Direccion.objects.create(
            calle="Av. Tecnologico",
            num_ext="1234",
            colonia="Centro",
            ciudad="Ciudad Juarez",
            estado="Chihuahua",
            cp="32500",
        )

        self.cliente.direccion_contacto = direccion
        self.cliente.save(
            update_fields=[
                "direccion_contacto",
                "updated_at",
            ]
        )

        self.vehiculo.placas = "ABC123"
        self.vehiculo.vin = "1HGBH41JXMN109186"
        self.vehiculo.save(
            update_fields=[
                "placas",
                "vin",
                "updated_at",
            ]
        )

        response = self.client.get(
            reverse(
                "portal:cotizacion_resumen_emision",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "portal/cotizacion_resumen_emision.html",
        )

        self.assertContains(
            response,
            "SOLM800101ABC",
        )

        self.assertContains(
            response,
            "ABC123",
        )

        self.assertContains(
            response,
            "DAÑOS MATERIALES",
        )

        self.assertContains(
            response,
            "ROBO TOTAL",
        )

        self.assertContains(
            response,
            "20398.28",
        )

    def test_conductor_post_normaliza_curp_a_mayusculas(
        self,
    ):
        self._set_public_session()

        self.item.seleccionada = True
        self.item.save(
            update_fields=["seleccionada"]
        )

        session = self.client.session
        session[
            "cotizacion_item_seleccionado_id"
        ] = self.item.id
        session.save()

        response = self.client.post(
            reverse(
                "portal:cotizacion_conductor",
                kwargs={
                    "pk": self.cotizacion.pk,
                },
            ),
            data={
                "nombre": "Miguel",
                "apellido_paterno": "Soto",
                "apellido_materno": "Lopez",
                "rfc": "solm800101abc",
                "curp": "solm800101hchxxx00",
                "fecha_nacimiento": "1980-01-01",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.cliente.refresh_from_db()

        self.assertEqual(
            self.cliente.curp,
            "SOLM800101HCHXXX00",
        )

class CotizacionVehiculoFormTests(TestCase):

    def test_vin_mayor_a_17_caracteres_es_invalido(self):
        form = CotizacionVehiculoForm(
            data={
                "placas": "ABC123",
                "vin": "123456789012345678",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("vin", form.errors)
