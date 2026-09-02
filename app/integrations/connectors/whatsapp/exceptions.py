from app.integrations.exceptions import IntegrationError


class WhatsAppApiError(IntegrationError):
    """Raised when WhatsApp Graph API request fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class WhatsAppAuthError(IntegrationError):
    """Raised when WhatsApp authentication / OAuth fails."""

    pass


class WhatsAppPublishError(IntegrationError):
    """Raised when WhatsApp message sending fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
