from app.integrations.exceptions import IntegrationError


class SlackError(IntegrationError):
    """Base exception for Slack errors."""

    pass


class SlackAuthError(SlackError):
    """Raised when Slack authentication fails (e.g., oauth.v2.access fails)."""

    pass


class SlackPublishError(SlackError):
    """Raised when a message fails to publish to a Slack channel."""

    pass


class SlackApiError(SlackError):
    """Raised when a generic Slack API call returns an error (ok=False)."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
