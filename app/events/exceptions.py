class EventException(Exception):
    """Base exception for all Event-related errors."""

    pass


class HandlerRegistrationError(EventException):
    """Raised when a handler cannot be registered."""

    pass


class EventDispatchError(EventException):
    """Raised when an event fails to dispatch to handlers."""

    pass
