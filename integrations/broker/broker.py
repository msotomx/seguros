# Aseguradoras

from integrations.broker.factory import get_provider


class InsuranceBroker:
    """
    Núcleo del Switchh Insurance Engine.

    Orquesta la comunicación entre el ERP y los Insurance Providers.

    Responsabilidades:
    - Localizar el Provider.
    - Ejecutar la operación solicitada.
    - Devolver un BrokerQuoteResult uniforme.

    No conoce APIs.
    No conoce JSON.
    No conoce modelos Django.
    """

    def quote(
        self,
        request,
        provider_code,
        provider_config,
    ):

        provider = get_provider(
            code=provider_code,
            provider_config=provider_config,
        )

        return provider.quote_auto(request)
    