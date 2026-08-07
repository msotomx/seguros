class ProviderError(Exception):
    """Error base para integraciones con aseguradoras."""


class ProviderAuthenticationError(ProviderError):
    """No fue posible autenticarse con el provider."""


class ProviderConfigurationError(ProviderError):
    """La configuración requerida del provider es inválida o incompleta."""


class ProviderQuoteError(ProviderError):
    """El provider no pudo generar una cotización."""


class ProviderUnsupportedOperationError(ProviderError):
    """El provider no soporta la operación solicitada."""
    
class ProviderHttpError(ProviderError):
    """Error genérico al comunicarse con un provider."""


class ProviderHttpTimeoutError(ProviderHttpError):
    """El provider excedió el tiempo máximo de respuesta."""


class ProviderHttpConnectionError(ProviderHttpError):
    """No fue posible establecer conexión con el provider."""


class ProviderHttpResponseError(ProviderHttpError):
    """El provider devolvió una respuesta HTTP no exitosa."""


class ProviderInvalidResponseError(ProviderHttpError):
    """El provider devolvió una respuesta inválida."""

class ProviderQuoteContextError(ProviderQuoteError):
    """No fue posible construir el contexto técnico de cotización."""
    