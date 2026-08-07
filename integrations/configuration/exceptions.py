class ProviderConfigurationError(Exception):
    """Error base relacionado con la configuración de Providers."""
    pass


class ProviderConfigurationNotFound(ProviderConfigurationError):
    """No existe una configuración activa para el Provider solicitado."""
    pass


class InvalidProviderSetting(ProviderConfigurationError):
    """Un parámetro del Provider tiene un valor o tipo inválido."""
    pass
