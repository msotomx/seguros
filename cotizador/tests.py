from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from autos.models import Vehiculo
from cotizador.models import Cotizacion
from crm.models import Cliente


class CotizacionConductorTests(TestCase):
    def test_guarda_datos_del_conductor(self):
        cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            email_principal="miguel@example.com",
        )

        vehiculo = Vehiculo.objects.create(
            cliente=cliente,
            marca_texto="Nissan",
            submarca_texto="Versa",
            modelo_anio=2024,
        )

        hoy = timezone.localdate()

        cotizacion = Cotizacion.objects.create(
            cliente=cliente,
            vehiculo=vehiculo,
            flotilla=None,
            tipo_cotizacion=Cotizacion.Tipo.INDIVIDUAL,
            vigencia_desde=hoy,
            vigencia_hasta=hoy + timedelta(days=365),
            conductor_nombre="Miguel",
            conductor_genero=(
                Cotizacion.GeneroConductor.MASCULINO
            ),
            conductor_edad=45,
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
