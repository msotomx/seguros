# PARA ASEGURADORAS

from abc import ABC, abstractmethod

from integrations.broker.contracts import (
    BrokerQuoteRequest,
    BrokerQuoteResult,
    BrokerIssueRequest,
    BrokerIssuedPolicy,
    BrokerPolicyDocument,
    BrokerPaymentLink,
)

class InsuranceProvider(ABC):
    code = None
    name = None

    @abstractmethod
    def health(self):
        pass

    @abstractmethod
    def quote_auto(self, request: BrokerQuoteRequest) -> BrokerQuoteResult:
        pass

    @abstractmethod
    def issue_policy(self, request: BrokerIssueRequest) -> BrokerIssuedPolicy:
        pass

    @abstractmethod
    def get_policy_document(self, policy_number: str) -> BrokerPolicyDocument:
        pass

    def get_payment_link(self, request: BrokerIssueRequest) -> BrokerPaymentLink:
        raise NotImplementedError("Este proveedor no implementa liga de pago.")
