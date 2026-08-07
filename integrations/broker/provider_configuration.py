from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderConfiguration:
    """
    Configuración operativa de un Insurance Provider.

    Representa la configuración general y los parámetros específicos
    necesarios para inicializar un Provider, sin exponer modelos Django
    al núcleo del Broker.
    """

    id: int
    provider: str
    ambiente: str
    ramo: str
    nombre: str

    aseguradora_id: int | None = None
    activo: bool = True
    prioridad: int = 100

    token_url: str = ""
    base_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    resource_id: str = ""
    api_version: str = "1"
    timeout: int = 30

    grouping_id: int | None = None
    rate_id: int | None = None
    business_profile_id: int | None = None
    business_profile_name: str = ""
    source_application_id: int | None = None

    supports_quote: bool = False
    supports_issue: bool = False
    supports_documents: bool = False
    supports_payments: bool = False
    supports_endorsements: bool = False
    supports_cancellation: bool = False
    supports_renewal: bool = False

    settings: dict[str, Any] = field(default_factory=dict)

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def require_setting(self, key: str) -> Any:
        value = self.get_setting(key)

        if value in (None, ""):
            raise ValueError(
                f"El Provider '{self.provider}' no tiene configurado "
                f"el parámetro obligatorio '{key}'."
            )

        return value

