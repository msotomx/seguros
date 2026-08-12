from django.test import TestCase

from portal.forms_public import CotizacionPublicaForm

from unittest.mock import patch

from django.urls import reverse

from autos.models import (
    Marca,
    SubMarca,
    Vehiculo,
    VehiculoCatalogo,
)
from cotizador.models import Cotizacion
from crm.models import Cliente, CodigoPostal


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
        }

    @patch(
        "portal.views.cotizar.RatingEngine.quote",
        return_value=[],
    )
    def test_post_crea_cliente_vehiculo_y_cotizacion(
        self,
        mock_quote,
    ):
        response = self.client.post(
            reverse("portal:cotizar"),
            data=self._post_data(),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("portal:cotizar_resumen"),
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

        # En esta etapa todavía no capturamos
        # datos necesarios exclusivamente para emisión.
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
            cotizacion.tipo_cotizacion,
            Cotizacion.Tipo.INDIVIDUAL,
        )

        self.assertEqual(
            cotizacion.origen,
            Cotizacion.Origen.PORTAL_PUBLICO,
        )

        self.assertEqual(
            cotizacion.estatus,
            Cotizacion.Estatus.BORRADOR,
        )

        self.assertEqual(
            cotizacion.codigo_postal,
            "32500",
        )

        self.assertEqual(
            cotizacion.ciudad,
            "Ciudad Juarez",
        )

        self.assertEqual(
            cotizacion.estado,
            "Chihuahua",
        )

        self.assertEqual(
            cotizacion.conductor_nombre,
            "Miguel",
        )

        self.assertEqual(
            cotizacion.conductor_genero,
            Cotizacion.GeneroConductor.MASCULINO,
        )

        self.assertEqual(
            cotizacion.conductor_edad,
            45,
        )

        # =================================================
        # Motor actual
        # =================================================

        mock_quote.assert_called_once_with(
            cotizacion,
        )

        # =================================================
        # Sesión pública
        # =================================================

        self.assertEqual(
            self.client.session[
                "cotizacion_publica_id"
            ],
            cotizacion.pk,
        )
