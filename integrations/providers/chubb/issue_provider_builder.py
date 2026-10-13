from __future__ import annotations

from integrations.configuration.exceptions import (
    InvalidProviderSetting,
)
from integrations.configuration.services import (
    ProviderConfigurationService,
)
from integrations.providers.chubb.internal_issue_mapper import (
    ChubbInternalIssueRequestMapper,
)
from integrations.providers.chubb.issue_client import (
    ChubbIssueClient,
)
from integrations.providers.chubb.issue_provider import (
    ChubbIssueProvider,
)


class ChubbIssueProviderBuilder:
    """
    Construye un ChubbIssueProvider listo para emitir.

    Responsabilidades:
    - obtener ProviderConfiguration;
    - validar que emisión esté habilitada;
    - validar provider_id;
    - construir el mapper interno;
    - construir el cliente de emisión;
    - ensamblar el provider.

    No realiza llamadas HTTP.
    No construye requests de negocio.
    No resuelve catálogos.
    No contiene valores operativos hardcodeados.
    """

    provider_code = "CHUBB"

    def __init__(
        self,
        *,
        configuration_service=ProviderConfigurationService,
        client_factory=ChubbIssueClient,
        mapper_factory=ChubbInternalIssueRequestMapper,
        provider_factory=ChubbIssueProvider,
    ) -> None:
        self._configuration_service = configuration_service
        self._client_factory = client_factory
        self._mapper_factory = mapper_factory
        self._provider_factory = provider_factory

    def build(
        self,
        *,
        ambiente: str,
        ramo: str,
        configuration=None,
    ) -> ChubbIssueProvider:
        if configuration is None:
            configuration = (
                self._configuration_service.get_active(
                    provider=self.provider_code,
                    ambiente=ambiente,
                    ramo=ramo,
                )
            )

        if not configuration.supports_issue:
            raise InvalidProviderSetting(
                "La configuración activa de Chubb no tiene "
                "habilitada la operación de emisión."
            )

        provider_id = self._required_positive_field(
            configuration,
            "id",
        )

        request_mapper = self._mapper_factory()

        client = self._client_factory(
            ambiente=ambiente,
            ramo=ramo,
            configuration_service=(
                self._configuration_service
            ),
            configuration=configuration,
        )

        return self._provider_factory(
            provider_id=provider_id,
            client=client,
            request_mapper=request_mapper,
        )

    @staticmethod
    def _required_field(
        configuration,
        field_name: str,
    ):
        value = getattr(
            configuration,
            field_name,
            None,
        )

        if value in (None, ""):
            raise InvalidProviderSetting(
                "La configuración de Chubb no contiene "
                f"el campo obligatorio '{field_name}'."
            )

        return value

    @classmethod
    def _required_positive_field(
        cls,
        configuration,
        field_name: str,
    ) -> int:
        value = cls._required_field(
            configuration,
            field_name,
        )

        if isinstance(value, bool):
            raise InvalidProviderSetting(
                f"'{field_name}' debe ser un entero positivo."
            )

        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidProviderSetting(
                f"'{field_name}' debe ser un entero positivo."
            ) from exc

        if normalized <= 0:
            raise InvalidProviderSetting(
                f"'{field_name}' debe ser un entero positivo."
            )

        return normalized
