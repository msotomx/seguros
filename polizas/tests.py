from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from autos.models import Vehiculo
from cotizador.models import Cotizacion, CotizacionItem
from crm.models import Cliente
from polizas.models import Poliza, PolizaProveedor
from catalogos.models import Aseguradora, ProductoSeguro


class PolizaProveedorTests(TestCase):

    def setUp(self):
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
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy,
            forma_pago_preferida="CONTADO",
        )

        self.aseguradora = Aseguradora.objects.create(
            nombre="Chubb Test",
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
            prima_neta=Decimal("35247.21"),
            derechos=Decimal("600.00"),
            iva=Decimal("5735.56"),
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
            provider="CHUBB",
            paquete_nombre="AMPLIA",
        )

        self.poliza = Poliza.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            aseguradora=self.aseguradora,
            producto=self.producto,
            cotizacion_item=self.item,
            numero_poliza="PEND-CHUBB-99007670",
            fecha_emision=hoy,
            vigencia_desde=hoy,
            vigencia_hasta=hoy,
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_neta=Decimal("35247.21"),
            financiamiento=Decimal("0.00"),
            gastos_expedicion=Decimal("600.00"),
            subtotal=Decimal("35847.21"),
            iva=Decimal("5735.56"),
            prima_total=Decimal("41582.77"),
            forma_pago="CONTADO",
        )

    def test_creates_provider_result(self):
        result = PolizaProveedor.objects.create(
            poliza=self.poliza,
            provider_code="CHUBB",
            provider_policy_id="99007670",
            provider_policy_key="M6",
            currency="MXN",
            raw_response={
                "success": True,
            },
        )

        self.assertEqual(
            result.poliza,
            self.poliza,
        )
        self.assertEqual(
            result.provider_code,
            "CHUBB",
        )
        self.assertEqual(
            result.provider_policy_id,
            "99007670",
        )
        self.assertEqual(
            result.provider_policy_key,
            "M6",
        )
        self.assertEqual(
            result.currency,
            "MXN",
        )

    def test_reverse_relation_from_poliza(self):
        result = PolizaProveedor.objects.create(
            poliza=self.poliza,
            provider_code="CHUBB",
            provider_policy_id="99007670",
            provider_policy_key="M6",
        )

        self.assertEqual(
            self.poliza.resultado_proveedor,
            result,
        )

    def test_rejects_duplicate_provider_policy(self):
        PolizaProveedor.objects.create(
            poliza=self.poliza,
            provider_code="CHUBB",
            provider_policy_id="99007670",
        )

        segunda_poliza = Poliza.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            aseguradora=self.aseguradora,
            producto=self.producto,
            cotizacion_item=None,
            numero_poliza="PEND-CHUBB-99007671",
            fecha_emision=timezone.localdate(),
            vigencia_desde=timezone.localdate(),
            vigencia_hasta=timezone.localdate(),
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_neta=Decimal("1.00"),
            financiamiento=Decimal("0.00"),
            gastos_expedicion=Decimal("0.00"),
            subtotal=Decimal("1.00"),
            iva=Decimal("0.00"),
            prima_total=Decimal("1.00"),
            forma_pago="CONTADO",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PolizaProveedor.objects.create(
                    poliza=segunda_poliza,
                    provider_code="CHUBB",
                    provider_policy_id="99007670",
                )

    def test_same_provider_policy_id_allowed_for_different_provider(self):
        PolizaProveedor.objects.create(
            poliza=self.poliza,
            provider_code="CHUBB",
            provider_policy_id="99007670",
        )

        otra_aseguradora = Aseguradora.objects.create(
            nombre="Otro Provider Test",
        )

        otro_producto = ProductoSeguro.objects.create(
            aseguradora=otra_aseguradora,
            nombre_producto="Autos Otro",
            tipo_producto=ProductoSeguro.TipoProducto.AUTO,
            modelo_calculo=ProductoSeguro.ModeloCalculo.SIMPLE,
        )

        segunda_poliza = Poliza.objects.create(
            cliente=self.cliente,
            vehiculo=self.vehiculo,
            aseguradora=otra_aseguradora,
            producto=otro_producto,
            numero_poliza="PEND-OTRO-99007670",
            fecha_emision=timezone.localdate(),
            vigencia_desde=timezone.localdate(),
            vigencia_hasta=timezone.localdate(),
            estatus=Poliza.Estatus.EN_PROCESO,
            prima_neta=Decimal("1.00"),
            financiamiento=Decimal("0.00"),
            gastos_expedicion=Decimal("0.00"),
            subtotal=Decimal("1.00"),
            iva=Decimal("0.00"),
            prima_total=Decimal("1.00"),
            forma_pago="CONTADO",
        )

        result = PolizaProveedor.objects.create(
            poliza=segunda_poliza,
            provider_code="OTRO",
            provider_policy_id="99007670",
        )

        self.assertEqual(
            result.provider_policy_id,
            "99007670",
        )
        self.assertEqual(
            result.provider_code,
            "OTRO",
        )
