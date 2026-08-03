import logging

from app.operations.errors.adapters import BaseErrorAdapter
from app.operations.logging.context import get_context_dict

logger = logging.getLogger(__name__)


class SentryAdapter(BaseErrorAdapter):
    """
    Mock implementation of Sentry adapter.
    In production, this would import sentry_sdk.
    """

    def capture_exception(
        self, exception: Exception, extras: dict | None = None
    ) -> None:
        context = get_context_dict()
        if extras:
            context.update(extras)
        logger.error(
            f"[SentryAdapter] Capturing exception: {exception} | Context: {context}"
        )
        # sentry_sdk.capture_exception(exception, extras=context)

    def capture_message(
        self, message: str, level: str = "info", extras: dict | None = None
    ) -> None:
        context = get_context_dict()
        if extras:
            context.update(extras)
        logger.info(
            f"[SentryAdapter] Capturing message ({level}): {message} | Context: {context}"
        )
        # sentry_sdk.capture_message(message, level=level, extras=context)
