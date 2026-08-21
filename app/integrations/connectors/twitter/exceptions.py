from app.integrations.exceptions import IntegrationError


class TwitterError(IntegrationError):
    """Base exception for all Twitter integration errors."""

    pass


class TwitterAuthError(TwitterError):
    """Raised when authentication or token exchange fails."""

    pass


class TwitterApiError(TwitterError):
    """Raised when a Twitter API call fails."""

    pass


class TwitterPublishError(TwitterError):
    """Raised when publishing a post fails."""

    pass
