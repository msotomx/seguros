from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from finanzas.models import Pago, PagoTransaccion
from finanzas.services.reconciliation import conciliar_pago_mercadopago


class MercadoPagoReconciliationTests(TestCase):

    @patch(
        "finanzas.services.reconciliation.aplicar_pago_a_objeto_negocio"
    )
    def test_pago_aprobado_se_concilia_correctamente(
        self,
        mock_aplicar_pago,
    ):
        pago = Pago.objects.create(
            monto=Decimal("1500.00"),
            moneda="MXN",
            fecha_programada=timezone.localdate(),
            estatus=Pago.Estatus.PENDIENTE,
        )

        payload = {
            "id": "MP-TEST-001",
            "status": "approved",
            "transaction_amount": 1500.00,
            "currency_id": "MXN",
            "payment_type_id": "credit_card",
            "external_reference": str(pago.id),
        }

        resultado = conciliar_pago_mercadopago(payload)

        pago.refresh_from_db()

        self.assertEqual(resultado.id, pago.id)
        self.assertEqual(pago.estatus, Pago.Estatus.PAGADO)
        self.assertEqual(pago.monto_pagado, Decimal("1500.00"))
        self.assertEqual(
            pago.provider,
            Pago.Provider.MERCADOPAGO,
        )
        self.assertEqual(
            pago.provider_payment_id,
            "MP-TEST-001",
        )
        self.assertIsNotNone(pago.fecha_pago)

        self.assertTrue(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.WEBHOOK_RECIBIDO,
            ).exists()
        )

        self.assertTrue(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.PAYMENT_APPROVED,
            ).exists()
        )

        mock_aplicar_pago.assert_called_once()

    @patch(
        "finanzas.services.reconciliation.aplicar_pago_a_objeto_negocio"
    )
    def test_webhook_duplicado_no_repite_efectos_de_negocio(
        self,
        mock_aplicar_pago,
    ):
        pago = Pago.objects.create(
            monto=Decimal("1500.00"),
            moneda="MXN",
            fecha_programada=timezone.localdate(),
            estatus=Pago.Estatus.PENDIENTE,
        )

        payload = {
            "id": "MP-TEST-002",
            "status": "approved",
            "transaction_amount": 1500.00,
            "currency_id": "MXN",
            "payment_type_id": "credit_card",
            "external_reference": str(pago.id),
        }

        # Primera confirmación
        conciliar_pago_mercadopago(payload)

        # Webhook duplicado
        conciliar_pago_mercadopago(payload)

        pago.refresh_from_db()

        self.assertEqual(pago.estatus, Pago.Estatus.PAGADO)

        # Los efectos de negocio se ejecutan una sola vez
        mock_aplicar_pago.assert_called_once()

        # Ambos webhooks quedan registrados
        self.assertEqual(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.WEBHOOK_RECIBIDO,
            ).count(),
            2,
        )

        # La conciliación aprobada se registra una sola vez
        self.assertEqual(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.PAYMENT_APPROVED,
            ).count(),
            1,
        )

    @patch(
        "finanzas.services.reconciliation.aplicar_pago_a_objeto_negocio"
    )
    def test_pago_pendiente_no_aplica_efectos_de_negocio(
        self,
        mock_aplicar_pago,
    ):
        pago = Pago.objects.create(
            monto=Decimal("1500.00"),
            moneda="MXN",
            fecha_programada=timezone.localdate(),
            estatus=Pago.Estatus.PENDIENTE,
        )

        payload = {
            "id": "MP-TEST-003",
            "status": "pending",
            "transaction_amount": 1500.00,
            "currency_id": "MXN",
            "payment_type_id": "credit_card",
            "external_reference": str(pago.id),
        }

        conciliar_pago_mercadopago(payload)

        pago.refresh_from_db()

        self.assertEqual(
            pago.estatus,
            Pago.Estatus.EN_PROCESO,
        )

        self.assertTrue(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.PAYMENT_PENDING,
            ).exists()
        )

        mock_aplicar_pago.assert_not_called()

    @patch(
        "finanzas.services.reconciliation.aplicar_pago_a_objeto_negocio"
    )
    def test_pago_rechazado_no_aplica_efectos_de_negocio(
        self,
        mock_aplicar_pago,
    ):
        pago = Pago.objects.create(
            monto=Decimal("1500.00"),
            moneda="MXN",
            fecha_programada=timezone.localdate(),
            estatus=Pago.Estatus.PENDIENTE,
        )

        payload = {
            "id": "MP-TEST-004",
            "status": "rejected",
            "transaction_amount": 1500.00,
            "currency_id": "MXN",
            "payment_type_id": "credit_card",
            "external_reference": str(pago.id),
        }

        conciliar_pago_mercadopago(payload)

        pago.refresh_from_db()

        self.assertEqual(
            pago.estatus,
            Pago.Estatus.RECHAZADO,
        )

        self.assertTrue(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.PAYMENT_REJECTED,
            ).exists()
        )

        self.assertIsNone(pago.fecha_pago)

        mock_aplicar_pago.assert_not_called()

    @patch(
        "finanzas.services.reconciliation.aplicar_pago_a_objeto_negocio"
    )
    def test_pago_parcial_no_aplica_efectos_de_negocio(
        self,
        mock_aplicar_pago,
    ):
        pago = Pago.objects.create(
            monto=Decimal("1500.00"),
            moneda="MXN",
            fecha_programada=timezone.localdate(),
            estatus=Pago.Estatus.PENDIENTE,
        )

        payload = {
            "id": "MP-TEST-005",
            "status": "approved",
            "transaction_amount": 1000.00,
            "currency_id": "MXN",
            "payment_type_id": "credit_card",
            "external_reference": str(pago.id),
        }

        conciliar_pago_mercadopago(payload)

        pago.refresh_from_db()

        self.assertEqual(
            pago.estatus,
            Pago.Estatus.PARCIAL,
        )

        self.assertEqual(
            pago.monto_pagado,
            Decimal("1000.00"),
        )

        self.assertEqual(
            pago.monto_pendiente,
            Decimal("500.00"),
        )

        self.assertIsNone(pago.fecha_pago)

        self.assertTrue(
            PagoTransaccion.objects.filter(
                pago=pago,
                tipo=PagoTransaccion.Tipo.PAYMENT_APPROVED,
            ).exists()
        )

        mock_aplicar_pago.assert_not_called()
