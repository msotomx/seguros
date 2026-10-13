from django.test import SimpleTestCase

from integrations.documents.contracts import PolicyDocumentRequest
from integrations.providers.chubb.internal_document_mapper import (
    ChubbInternalDocumentRequestMapper,
)


class ChubbInternalDocumentRequestMapperTests(SimpleTestCase):
    def test_maps_internal_request_to_chubb_request(self):
        mapper = ChubbInternalDocumentRequestMapper(
            generate_all_receipts=True,
            copies=0,
        )

        request = PolicyDocumentRequest(
            provider_policy_id="99007704",
            provider_policy_key=" M6 ",
            risk_number=1,
        )

        result = mapper.map(request)

        self.assertEqual(result.policy_id, 99007704)
        self.assertEqual(result.policy_key, "M6")
        self.assertEqual(result.risk_number, 1)
        self.assertTrue(result.generate_all_receipts)
        self.assertEqual(result.copies, 0)

    def test_rejects_non_numeric_chubb_policy_id(self):
        mapper = ChubbInternalDocumentRequestMapper(
            generate_all_receipts=True,
            copies=0,
        )

        request = PolicyDocumentRequest(
            provider_policy_id="POL-123",
            provider_policy_key="M6",
            risk_number=1,
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_policy_id debe ser numérico para Chubb",
        ):
            mapper.map(request)

    def test_rejects_empty_policy_key(self):
        mapper = ChubbInternalDocumentRequestMapper(
            generate_all_receipts=True,
            copies=0,
        )

        request = PolicyDocumentRequest(
            provider_policy_id="99007704",
            provider_policy_key=" ",
            risk_number=1,
        )

        with self.assertRaisesRegex(
            ValueError,
            "provider_policy_key es requerido",
        ):
            mapper.map(request)

    def test_rejects_negative_copies(self):
        with self.assertRaisesRegex(
            ValueError,
            "copies no puede ser negativo",
        ):
            ChubbInternalDocumentRequestMapper(
                generate_all_receipts=True,
                copies=-1,
            )
