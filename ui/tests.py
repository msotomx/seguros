from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from autos.models import Vehiculo
from catalogos.models import Aseguradora, ProductoSeguro
from cotizador.models import Cotizacion, CotizacionItem
from crm.models import Cliente
from polizas.models import Poliza
from django.contrib.auth.models import Permission

class CotizacionEmitirPolizaViewTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="agente_test",
            password="test12345",
        )

        permission = Permission.objects.get(
            codename="add_poliza",
            content_type__app_label="polizas",
        )

        self.user.user_permissions.add(permission)

        self.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        self.vehiculo = Vehiculo.objects.create(
            cliente=self.cliente,
            marca_texto="ACURA",
            submarca_texto="TL",
            modelo_anio=2015,
            version="SEDAN 3.7L AUT",
            placas="TR543",
            vin="JH4KA3277KC007500",
        )

        hoy = timezone.localdate()

        self.cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            forma_pago_preferida="CONTADO",
            owner=self.user,
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb UI Test",
        )

        self.producto = ProductoSeguro.objects.create(
            aseguradora=self.aseguradora,
            nombre_producto="Autos",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            aseguradora=self.aseguradora,
            producto=self.producto,
            prima_neta=Decimal("35000.00"),
            derechos=Decimal("500.00"),
            iva=Decimal("5680.00"),
            prima_total=Decimal("41180.00"),
            forma_pago="CONTADO",
            provider="CHUBB",
            provider_quote_id="2061261215",
            paquete_nombre="AMPLIA",
        )

        self.client.force_login(self.user)

    @patch(
        "ui.views.cotizaciones."
        "PortalIssueApplicationService.issue_one"
    )
    def test_emitir_poliza_uses_application_service(
        self,
        mock_issue_one,
    ):
        def issue_side_effect(*, cotizacion_item):
            return Poliza.objects.create(
                cliente=self.cliente,
                vehiculo=self.vehiculo,
                aseguradora=self.aseguradora,
                producto=self.producto,
                cotizacion_item=cotizacion_item,
                numero_poliza="PEND-CHUBB-99007670",
                fecha_emision=timezone.localdate(),
                vigencia_desde=self.cotizacion.vigencia_desde,
                vigencia_hasta=self.cotizacion.vigencia_hasta,
                estatus=Poliza.Estatus.EN_PROCESO,
                prima_neta=Decimal("35247.21"),
                financiamiento=Decimal("0.00"),
                gastos_expedicion=Decimal("600.00"),
                subtotal=Decimal("35847.21"),
                iva=Decimal("5735.56"),
                prima_total=Decimal("41582.77"),
                forma_pago="CONTADO",
                agente=self.user,
            )

        mock_issue_one.side_effect = issue_side_effect

        self.assertFalse(
            Poliza.objects.filter(
                cotizacion_item=self.item,
            ).exists()
        )

        response = self.client.post(
            reverse(
                "ui:cotizacion_emitir_poliza",
                kwargs={"pk": self.cotizacion.pk},
            ),
            {
                "selected_item_id": self.item.pk,
            },
        )

        mock_issue_one.assert_called_once_with(
            cotizacion_item=self.item,
        )

        self.assertRedirects(
            response,
            reverse("ui:poliza_list"),
        )

        self.assertEqual(
            Poliza.objects.filter(
                cotizacion_item=self.item,
            ).count(),
            1,
        )

    @patch(
        "ui.views.cotizaciones."
        "PortalIssueApplicationService.issue_one"
    )
    def test_emitir_poliza_failure_does_not_create_policy(
        self,
        mock_issue_one,
    ):
        estado_inicial = self.cotizacion.estatus

        mock_issue_one.side_effect = ValueError(
            "Error de emisión del proveedor."
        )

        response = self.client.post(
            reverse(
                "ui:cotizacion_emitir_poliza",
                kwargs={"pk": self.cotizacion.pk},
            ),
            {
                "selected_item_id": self.item.pk,
            },
        )

        mock_issue_one.assert_called_once_with(
            cotizacion_item=self.item,
        )

        self.assertRedirects(
            response,
            reverse(
                "ui:cotizacion_detail",
                kwargs={"pk": self.cotizacion.pk},
            ),
            fetch_redirect_response=False,
        )

        self.assertFalse(
            Poliza.objects.filter(
                cotizacion_item=self.item,
            ).exists()
        )

        self.cotizacion.refresh_from_db()

        self.assertEqual(
            self.cotizacion.estatus,
            estado_inicial,
        )

        self.assertIsNone(
            self.cotizacion.emitida_at,
        )
