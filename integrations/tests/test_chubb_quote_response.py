from decimal import Decimal

from django.test import SimpleTestCase

from integrations.providers.chubb.responses import (
    ChubbQuoteResponseMapper,
)
from integrations.providers.exceptions import (
    ProviderInvalidResponseError,
    ProviderQuoteError,
)


class ChubbQuoteResponseMapperTest(SimpleTestCase):
    def setUp(self):
        self.payload = {
            "success": True,
            "messages": [],
            "responseData": {
                "quoteId": 124469636,
                "quoteVersionId": 126717156,
                "baseNetPremium": 22496.0085,
                "baseNetPremiumWithoutDiscount": 24995.565,
                "discounts": [
                    {
                        "discountTypeId": 1,
                        "discountTag": "Descuento",
                        "discountPercentage": 10.0,
                        "discountAmount": 2499.5565,
                    }
                ],
                "surchargeAmount": 0.0,
                "feeAmount": 3000.0,
                "taxAmount": 4079.3614,
                "totalPremiumAmount": 29575.3699,
            },
        }

    def test_maps_successful_quote(self):
        result = ChubbQuoteResponseMapper.map(
            provider_id=1,
            payload=self.payload,
        )

        self.assertEqual(result.provider_id, 1)
        self.assertEqual(
            result.provider_quote_id,
            "124469636",
        )
        self.assertEqual(result.status, "QUOTED")

        self.assertEqual(
            result.amount.net_premium,
            Decimal("22496.0085"),
        )
        self.assertEqual(
            result.amount.fees,
            Decimal("3000.0"),
        )
        self.assertEqual(
            result.amount.taxes,
            Decimal("4079.3614"),
        )
        self.assertEqual(
            result.amount.total,
            Decimal("29575.3699"),
        )
        self.assertEqual(
            result.amount.currency,
            "MXN",
        )

    def test_maps_quote_version_to_metadata(self):
        result = ChubbQuoteResponseMapper.map(
            provider_id=1,
            payload=self.payload,
        )

        self.assertEqual(
            result.metadata["quote_version_id"],
            "126717156",
        )
        self.assertEqual(
            result.metadata[
                "base_net_premium_without_discount"
            ],
            Decimal("24995.565"),
        )

    def test_preserves_raw_response(self):
        result = ChubbQuoteResponseMapper.map(
            provider_id=1,
            payload=self.payload,
        )

        self.assertEqual(
            result.raw_response,
            self.payload,
        )

    def test_rejects_unsuccessful_quote(self):
        payload = {
            "success": False,
            "messages": [
                {
                    "message": "Vehículo no encontrado",
                    "messageCode": 1001,
                    "messageType": 2,
                }
            ],
            "responseData": None,
        }

        with self.assertRaises(
            ProviderQuoteError
        ) as context:
            ChubbQuoteResponseMapper.map(
                provider_id=1,
                payload=payload,
            )

        self.assertIn(
            "Vehículo no encontrado",
            str(context.exception),
        )
        self.assertIn(
            "1001",
            str(context.exception),
        )

    def test_rejects_missing_response_data(self):
        payload = {
            "success": True,
            "messages": [],
        }

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            ChubbQuoteResponseMapper.map(
                provider_id=1,
                payload=payload,
            )

    def test_rejects_missing_quote_id(self):
        payload = {
            "success": True,
            "messages": [],
            "responseData": {
                "quoteVersionId": 126717156,
                "baseNetPremium": 1000,
                "feeAmount": 100,
                "taxAmount": 160,
                "totalPremiumAmount": 1260,
            },
        }

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            ChubbQuoteResponseMapper.map(
                provider_id=1,
                payload=payload,
            )

    def test_rejects_invalid_total(self):
        payload = {
            "success": True,
            "messages": [],
            "responseData": {
                "quoteId": 1,
                "quoteVersionId": 2,
                "baseNetPremium": 1000,
                "feeAmount": 100,
                "taxAmount": 160,
                "totalPremiumAmount": "INVALID",
            },
        }

        with self.assertRaises(
            ProviderInvalidResponseError
        ):
            ChubbQuoteResponseMapper.map(
                provider_id=1,
                payload=payload,
            )

    def test_null_optional_amounts_default_to_zero(self):
        payload = {
            "success": True,
            "messages": [],
            "responseData": {
                "quoteId": 1,
                "quoteVersionId": 2,
                "baseNetPremium": 1000,
                "feeAmount": None,
                "taxAmount": None,
                "totalPremiumAmount": 1000,
            },
        }

        result = ChubbQuoteResponseMapper.map(
            provider_id=1,
            payload=payload,
        )

        self.assertEqual(
            result.amount.fees,
            Decimal("0"),
        )
        self.assertEqual(
            result.amount.taxes,
            Decimal("0"),
        )
        