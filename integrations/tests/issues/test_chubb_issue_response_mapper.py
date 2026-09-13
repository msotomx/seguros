from unittest import TestCase

from integrations.providers.chubb.issue_mappers import (
    ChubbIssueResponseMapper,
)


class ChubbIssueResponseMapperTests(TestCase):

    def test_issue_maps_successful_response(self):
        payload = {
            "success": True,
            "messages": None,
            "responseData": [
                {
                    "quoteKey": "M6 ",
                    "quotePolicyId": 99007664,
                    "netPremiumAmount": 35247.21,
                    "bonificationAmount": 0.0,
                    "surchargeAmount": 0.0,
                    "discountAmount": 0.0,
                    "totalPremiumAmount": 41582.77,
                    "insuredId": 18683522,
                    "insuredAddressId": 1410484013,
                    "items": [
                        {
                            "item": {
                                "number": 1,
                                "netPremiumAmount": 35247.21,
                                "rightAmount": 600.0,
                                "discountAmount": 0.0,
                                "surchargeAmount": 0.0,
                                "ivaAmount": 5735.56,
                                "totalPremiumAmount": 41582.77,
                            }
                        }
                    ],
                }
            ],
        }

        result = ChubbIssueResponseMapper.issue(
            payload
        )

        self.assertEqual(
            result.quote_key,
            "M6",
        )
        self.assertEqual(
            result.quote_policy_id,
            99007664,
        )
        self.assertEqual(
            result.total_premium_amount,
            41582.77,
        )
        self.assertEqual(
            result.insured_id,
            18683522,
        )

        self.assertEqual(
            len(result.items),
            1,
        )

        item = result.items[0]

        self.assertEqual(
            item.number,
            1,
        )
        self.assertEqual(
            item.right_amount,
            600.0,
        )
        self.assertEqual(
            item.iva_amount,
            5735.56,
        )

    def test_issue_accepts_is_success_wrapper(self):
        payload = {
            "isSuccess": False,
            "messages": [
                {
                    "message": (
                        "La cotización enviada ya fue emitida "
                        "con número de póliza K6 99454302"
                    ),
                    "messageCode": 0,
                    "messageType": 2,
                }
            ],
            "responseData": None,
        }

        with self.assertRaisesRegex(
            ValueError,
            "ya fue emitida",
        ):
            ChubbIssueResponseMapper.issue(
                payload
            )

    def test_issue_raises_business_error_message(self):
        payload = {
            "success": False,
            "messages": [
                {
                    "message": (
                        "Inciso 1: El número de serie "
                        "ya existe en la póliza 123."
                    ),
                    "messageCode": 0,
                    "messageType": 2,
                }
            ],
            "responseData": None,
        }

        with self.assertRaisesRegex(
            ValueError,
            "número de serie",
        ):
            ChubbIssueResponseMapper.issue(
                payload
            )

    def test_issue_requires_success_indicator(self):
        payload = {
            "messages": None,
            "responseData": None,
        }

        with self.assertRaisesRegex(
            ValueError,
            "success ni isSuccess",
        ):
            ChubbIssueResponseMapper.issue(
                payload
            )

    def test_issue_rejects_empty_response_data(self):
        payload = {
            "success": True,
            "messages": None,
            "responseData": [],
        }

        with self.assertRaisesRegex(
            ValueError,
            "responseData no puede estar vacío",
        ):
            ChubbIssueResponseMapper.issue(
                payload
            )
