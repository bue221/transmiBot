class TransmiBotError(Exception):
    """Base exception for domain-specific errors."""


class ConfigurationError(TransmiBotError):
    """Raised when required settings are missing or invalid."""


class ExternalServiceError(TransmiBotError):
    """Raised when external services (Telegram, Google ADK) fail."""

