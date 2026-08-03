from app.integrations.exceptions import IntegrationError


class FacebookError(IntegrationError):
    """Base exception for Facebook errors."""

    pass


class FacebookAuthError(FacebookError):
    """Raised when Facebook authentication fails (e.g. token exchange, long-lived token)."""

    pass


class FacebookPublishError(FacebookError):
    """Raised when a post fails to publish to a Facebook Page."""

    pass


class FacebookApiError(FacebookError):
    """Raised when the Facebook Graph API returns an error response."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}
