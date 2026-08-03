from app.integrations.exceptions import IntegrationError


class GoogleError(IntegrationError):
    """Base exception for Google errors."""

    pass


class GoogleAuthError(GoogleError):
    """Raised when Google authentication fails (e.g. token exchange, refresh)."""

    pass


class GoogleApiError(GoogleError):
    """Raised when the Google API returns an error response."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class GoogleQuotaError(GoogleApiError):
    """Raised when a Google API quota is exceeded (429 or 403 reason: quotaExceeded)."""

    pass
