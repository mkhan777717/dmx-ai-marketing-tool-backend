from abc import ABC, abstractmethod


class BaseErrorAdapter(ABC):
    """
    Abstract interface for Error Tracking providers (Sentry, DataDog, etc.)
    """

    @abstractmethod
    def capture_exception(
        self, exception: Exception, extras: dict | None = None
    ) -> None:
        pass

    @abstractmethod
    def capture_message(
        self, message: str, level: str = "info", extras: dict | None = None
    ) -> None:
        pass
