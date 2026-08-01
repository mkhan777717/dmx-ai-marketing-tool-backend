from app.integrations.exceptions import IntegrationError


class InstagramError(IntegrationError):
    """Base exception for Instagram errors."""

    pass


class InstagramAuthError(InstagramError):
    """Raised when Instagram authentication fails (e.g. token exchange)."""

    pass


class InstagramPublishError(InstagramError):
    """Raised when a post fails to publish to an Instagram Business Account."""

    pass


class InstagramApiError(InstagramError):
    """Raised when the Instagram Graph API returns an error response."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}
