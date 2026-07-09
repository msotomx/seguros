from integrations.broker.base import InsuranceProvider
from integrations.broker.contracts import (
    BrokerQuoteRequest,
    BrokerQuoteResult,
    BrokerIssueRequest,
    BrokerIssuedPolicy,
    BrokerPolicyDocument,
)
from integrations.broker.exceptions import InsuranceProviderUnavailable

from integrations.providers.insurance.chubb.services.catalog_service import ChubbCatalogService
from integrations.providers.insurance.chubb.services.quote_service import ChubbQuoteService


class ChubbProvider(InsuranceProvider):
    """
    Implementación del Provider para la aseguradora Chubb.

    Expone la interfaz pública utilizada por el Insurance Broker y delega
    cada operación al Service correspondiente.

    Responsabilidades:
    - Representar la integración con Chubb.
    - Exponer los casos de uso soportados (cotización, emisión, documentos).
    - Delegar la ejecución a los Services especializados.
    - Mantener una interfaz uniforme para el Insurance Broker.

    No construye payloads.
    No interpreta respuestas.
    No realiza lógica de negocio.
    No conoce modelos Django.
    """

    code = "CHUBB"
    name = "Chubb"

    def __init__(self, provider_config=None):
        self.provider_config = provider_config
        self.catalogs = ChubbCatalogService()
        self.quote_service = ChubbQuoteService()

    def health(self):
        return self.catalogs.health()

    def quote_auto(self, request: BrokerQuoteRequest) -> BrokerQuoteResult:
        if not self.provider_config:
            result = BrokerQuoteResult(request=request)
            result.errors.append({
                "provider": self.code,
                "error": "ChubbProvider no tiene provider_config configurado.",
            })
            return result

        return self.quote_service.create_quote(
            request=request,
            provider_config=self.provider_config,
        )

    def issue_policy(self, request: BrokerIssueRequest) -> BrokerIssuedPolicy:
        raise InsuranceProviderUnavailable("Emisión Chubb pendiente de implementar.")

    def get_policy_document(self, policy_number: str) -> BrokerPolicyDocument:
        raise InsuranceProviderUnavailable("Documentos Chubb pendiente de implementar.")