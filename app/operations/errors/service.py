from app.operations.errors.adapters import BaseErrorAdapter
from app.operations.errors.adapters.sentry import SentryAdapter


class ErrorService:
    """
    Facade for error tracking. Business logic uses this service
    so it is completely decoupled from Sentry.
    """

    def __init__(self, adapter: BaseErrorAdapter):
        self._adapter = adapter

    def capture_exception(
        self, exception: Exception, extras: dict | None = None
    ) -> None:
        self._adapter.capture_exception(exception, extras)

    def capture_message(
        self, message: str, level: str = "info", extras: dict | None = None
    ) -> None:
        self._adapter.capture_message(message, level, extras)


# Global singleton
error_service = ErrorService(adapter=SentryAdapter())
