from app.integrations.exceptions import IntegrationError


class LinkedInError(IntegrationError):
    """Base exception for LinkedIn errors."""

    pass


class LinkedInAuthError(LinkedInError):
    """Raised when LinkedIn authentication fails."""

    pass


class LinkedInPublishError(LinkedInError):
    """Raised when a post fails to publish to LinkedIn."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LinkedInApiError(LinkedInError):
    """Raised when the LinkedIn API returns an error response."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}
