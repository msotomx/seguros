
from datetime import date

from django.test import TestCase

from crm.models import Cliente


class ClienteTests(TestCase):

    def test_cliente_persona_guarda_fecha_nacimiento_y_genero(self):
        cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PERSONA,
            nombre="Miguel",
            apellido_paterno="Soto",
            apellido_materno="",
            fecha_nacimiento=date(1990, 5, 15),
            genero=Cliente.Genero.MASCULINO,
        )

        cliente.refresh_from_db()

        self.assertEqual(
            cliente.fecha_nacimiento,
            date(1990, 5, 15),
        )
        self.assertEqual(
            cliente.genero,
            Cliente.Genero.MASCULINO,
        )
