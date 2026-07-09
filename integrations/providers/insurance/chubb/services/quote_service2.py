from integrations.providers.insurance.chubb.api_client import ChubbApiClient
from integrations.providers.insurance.chubb.builders.quote_builder import ChubbQuoteBuilder
from integrations.providers.insurance.chubb.mappers.quote_mapper import ChubbQuoteMapper


class ChubbQuoteService:
    """
    Orquesta el proceso de cotización con Chubb.

    Coordina la construcción del payload, la comunicación con la API de Chubb
    y la conversión de la respuesta al modelo de dominio del Broker.

    Flujo:
    BrokerQuoteRequest
        ↓
    ChubbQuoteBuilder
        ↓
    ChubbApiClient
        ↓
    ChubbQuoteMapper
        ↓
    BrokerQuoteResult

    Responsabilidades:
    - Coordinar el proceso de cotización.
    - Invocar el Quote Builder.
    - Consumir el endpoint POST /quote mediante el API Client.
    - Convertir la respuesta utilizando el Quote Mapper.

    No construye payloads.
    No interpreta respuestas.
    No conoce modelos Django.
    No contiene lógica de negocio.
    
    """

    def __init__(self, client=None, builder=None, mapper=None):
        self.client = client or ChubbApiClient()
        self.builder = builder or ChubbQuoteBuilder()
        self.mapper = mapper or ChubbQuoteMapper()

    def create_quote(self, request, provider_config):
        payload = self.builder.build(
            request=request,
            provider_config=provider_config,
        )

        response = self.client.post_quote(payload)

        return self.mapper.map(
            request=request,
            response=response,
        )
    