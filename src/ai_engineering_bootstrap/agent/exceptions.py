"""Custom exceptions for Agent Provider errors."""


class ProviderError(Exception):
    """Base exception for provider-related errors."""


class ProviderConnectionError(ProviderError):
    """Raised when connection to the provider fails."""


class ProviderTimeoutError(ProviderError):
    """Raised when a request to the provider times out."""


class ProviderResponseError(ProviderError):
    """Raised when the provider returns an invalid or error response."""


__all__ = [
    "ProviderConnectionError",
    "ProviderError",
    "ProviderResponseError",
    "ProviderTimeoutError",
]
