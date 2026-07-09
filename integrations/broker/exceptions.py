
class BrokerError(Exception):
    """Excepción base del Motor Broker."""
    pass


class InsuranceProviderUnavailable(BrokerError):
    """El proveedor no está disponible o no puede atender la solicitud."""
    pass


class InsuranceQuoteError(BrokerError):
    """Error durante el proceso de cotización."""
    pass


class InsuranceIssueError(BrokerError):
    """Error durante la emisión de la póliza."""
    pass


class InsuranceAuthenticationError(BrokerError):
    pass


class InsuranceAuthorizationError(BrokerError):
    pass


class InsuranceTimeoutError(BrokerError):
    pass


class InsurancePolicyError(BrokerError):
    pass


class InsuranceDocumentError(BrokerError):
    pass
