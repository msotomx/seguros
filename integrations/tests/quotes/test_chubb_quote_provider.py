from unittest import TestCase
from unittest.mock import Mock, patch

from integrations.providers.chubb.quote_contracts import (
    ChubbCreateQuoteRequest,
    ChubbCreateQuoteResult,
)
from integrations.providers.chubb.quote_provider import (
    ChubbQuoteProvider,
)
from integrations.quotes.contracts import (
    InternalQuoteRequest,
    QuoteResult,
)


class ChubbQuoteProviderTests(TestCase):
    def setUp(self) -> None:
        self.client = Mock()
        self.request_mapper = Mock()

        self.provider = ChubbQuoteProvider(
            client=self.client,
            request_mapper=self.request_mapper,
        )

        self.internal_request = Mock(
            spec=InternalQuoteRequest,
        )

        self.chubb_request = Mock(
            spec=ChubbCreateQuoteRequest,
        )

        self.chubb_result = Mock(
            spec=ChubbCreateQuoteResult,
        )

        self.quote_result = Mock(
            spec=QuoteResult,
        )

        self.request_mapper.create_quote.return_value = (
            self.chubb_request
        )

        self.client.create_quote.return_value = (
            self.chubb_result
        )

    def test_provider_code_is_chubb(self):
        self.assertEqual(
            self.provider.provider_code,
            "CHUBB",
        )

    @patch(
        "integrations.providers.chubb.quote_provider."
        "ChubbQuoteAdapter.to_quote_result"
    )
    def test_quote_executes_complete_pipeline(
        self,
        adapter_mock,
    ):
        adapter_mock.return_value = self.quote_result

        result = self.provider.quote(
            self.internal_request
        )

        self.assertIs(
            result,
            self.quote_result,
        )

        self.request_mapper.create_quote.assert_called_once_with(
            self.internal_request
        )

        self.client.create_quote.assert_called_once_with(
            self.chubb_request
        )

        adapter_mock.assert_called_once_with(
            self.chubb_result
        )

    @patch(
        "integrations.providers.chubb.quote_provider."
        "ChubbQuoteAdapter.to_quote_result"
    )
    def test_quote_executes_operations_in_expected_order(
        self,
        adapter_mock,
    ):
        calls = []

        def map_request(request):
            calls.append("request_mapper")
            return self.chubb_request

        def create_quote(request):
            calls.append("client")
            return self.chubb_result

        def adapt_result(result):
            calls.append("adapter")
            return self.quote_result

        self.request_mapper.create_quote.side_effect = (
            map_request
        )
        self.client.create_quote.side_effect = (
            create_quote
        )
        adapter_mock.side_effect = adapt_result

        result = self.provider.quote(
            self.internal_request
        )

        self.assertIs(
            result,
            self.quote_result,
        )
        self.assertEqual(
            calls,
            [
                "request_mapper",
                "client",
                "adapter",
            ],
        )

    @patch(
        "integrations.providers.chubb.quote_provider."
        "ChubbQuoteAdapter.to_quote_result"
    )
    def test_quote_does_not_call_client_when_mapper_fails(
        self,
        adapter_mock,
    ):
        mapper_error = ValueError(
            "Solicitud interna inválida."
        )
        self.request_mapper.create_quote.side_effect = (
            mapper_error
        )

        with self.assertRaises(ValueError) as context:
            self.provider.quote(
                self.internal_request
            )

        self.assertIs(
            context.exception,
            mapper_error,
        )
        self.client.create_quote.assert_not_called()
        adapter_mock.assert_not_called()

    @patch(
        "integrations.providers.chubb.quote_provider."
        "ChubbQuoteAdapter.to_quote_result"
    )
    def test_quote_does_not_call_adapter_when_client_fails(
        self,
        adapter_mock,
    ):
        client_error = RuntimeError(
            "No fue posible cotizar con Chubb."
        )
        self.client.create_quote.side_effect = (
            client_error
        )

        with self.assertRaises(RuntimeError) as context:
            self.provider.quote(
                self.internal_request
            )

        self.assertIs(
            context.exception,
            client_error,
        )
        adapter_mock.assert_not_called()

    @patch(
        "integrations.providers.chubb.quote_provider."
        "ChubbQuoteAdapter.to_quote_result"
    )
    def test_quote_propagates_adapter_error(
        self,
        adapter_mock,
    ):
        adapter_error = ValueError(
            "Resultado Chubb inválido."
        )
        adapter_mock.side_effect = adapter_error

        with self.assertRaises(ValueError) as context:
            self.provider.quote(
                self.internal_request
            )

        self.assertIs(
            context.exception,
            adapter_error,
        )
