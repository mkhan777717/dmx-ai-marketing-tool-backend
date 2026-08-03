class IntegrationError(Exception):
    """Base exception for integration errors."""

    pass


class CircuitBreakerOpenError(IntegrationError):
    """Raised when the circuit breaker is open and blocks a request."""

    pass


class RateLimitExceededError(IntegrationError):
    """Raised when a provider's rate limit is exceeded."""

    pass


class OAuthTokenError(IntegrationError):
    """Raised when an OAuth token is invalid, expired, or failed to refresh."""

    pass


class WebhookVerificationError(IntegrationError):
    """Raised when a webhook payload fails signature verification."""

    pass
