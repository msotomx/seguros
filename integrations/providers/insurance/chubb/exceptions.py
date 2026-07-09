class ChubbProviderError(Exception):
    """Excepción base para errores específicos del proveedor Chubb."""
    pass


class ChubbAuthenticationError(ChubbProviderError):
    """Error de autenticación (obtención o uso del token)."""
    pass


class ChubbAuthorizationError(ChubbProviderError):
    """El token es válido pero no tiene permisos para consumir el recurso."""
    pass


class ChubbApiError(ChubbProviderError):
    """Error devuelto por la API de Chubb."""
    pass


class ChubbTimeoutError(ChubbProviderError):
    """Tiempo de espera agotado al consumir la API."""
    pass