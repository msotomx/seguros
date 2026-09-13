from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase

from integrations.persons.contracts import PersonResult


class CotizacionPersonSitCommandTests(
    SimpleTestCase
):

    def _cotizacion(self):
        cliente = Mock()
        cliente.nombre_mostrar = "Miguel Soto"

        cotizacion = Mock()
        cotizacion.id = 3
        cotizacion.folio = "COT-2026-000003"
        cotizacion.cliente = cliente

        return cotizacion

    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit."
        "PortalPersonApplicationService.create_one"
    )
    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit.Cotizacion.objects"
    )
    def test_sin_send_no_ejecuta_create_person(
        self,
        objects,
        create_one,
    ):
        cotizacion = self._cotizacion()

        objects.select_related.return_value.get.return_value = (
            cotizacion
        )

        stdout = StringIO()

        call_command(
            "cotizacion_person_sit",
            cotizacion_id=3,
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            stdout=stdout,
        )

        create_one.assert_not_called()

        self.assertIn(
            "No se realizó llamada al provider",
            stdout.getvalue(),
        )

    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit."
        "PortalPersonApplicationService.create_one"
    )
    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit.Cotizacion.objects"
    )
    def test_send_ejecuta_application_service(
        self,
        objects,
        create_one,
    ):
        cotizacion = self._cotizacion()

        objects.select_related.return_value.get.return_value = (
            cotizacion
        )

        create_one.return_value = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="60486498",
            provider_person_id="18683522",
            provider_address_id="1410484013",
            raw_response={
                "tranId": 60486498,
                "personId": 18683522,
                "addressId": 1410484013,
            },
        )

        stdout = StringIO()

        call_command(
            "cotizacion_person_sit",
            cotizacion_id=3,
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            send=True,
            stdout=stdout,
        )

        create_one.assert_called_once_with(
            cotizacion=cotizacion,
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
        )

        output = stdout.getvalue()

        self.assertIn(
            "60486498",
            output,
        )
        self.assertIn(
            "18683522",
            output,
        )
        self.assertIn(
            "1410484013",
            output,
        )

    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit."
        "PortalPersonApplicationService.create_one"
    )
    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit.Cotizacion.objects"
    )
    def test_show_response_muestra_raw_response(
        self,
        objects,
        create_one,
    ):
        cotizacion = self._cotizacion()

        objects.select_related.return_value.get.return_value = (
            cotizacion
        )

        create_one.return_value = PersonResult(
            provider_code="CHUBB",
            provider_tran_id="60486498",
            provider_person_id="18683522",
            provider_address_id="1410484013",
            raw_response={
                "tranId": 60486498,
                "personId": 18683522,
                "addressId": 1410484013,
            },
        )

        stdout = StringIO()

        call_command(
            "cotizacion_person_sit",
            cotizacion_id=3,
            provider_code="CHUBB",
            ambiente="SIT",
            ramo="AUTOS",
            send=True,
            show_response=True,
            stdout=stdout,
        )

        output = stdout.getvalue()

        self.assertIn(
            '"tranId": 60486498',
            output,
        )
        self.assertIn(
            '"personId": 18683522',
            output,
        )

    @patch(
        "integrations.management.commands."
        "cotizacion_person_sit.Cotizacion.objects"
    )
    def test_cotizacion_inexistente_lanza_error(
        self,
        objects,
    ):
        from cotizador.models import Cotizacion

        objects.select_related.return_value.get.side_effect = (
            Cotizacion.DoesNotExist
        )

        with self.assertRaisesRegex(
            Exception,
            "No existe Cotizacion",
        ):
            call_command(
                "cotizacion_person_sit",
                cotizacion_id=999,
                provider_code="CHUBB",
                ambiente="SIT",
                ramo="AUTOS",
            )
