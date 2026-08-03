import asyncio
import logging
from functools import wraps
from typing import Callable

from app.integrations.exceptions import CircuitBreakerOpenError

logger = logging.getLogger(__name__)


def retry_policy(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    expected_exceptions: tuple = (Exception,),
):
    """
    Exponential backoff retry decorator.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            while True:
                try:
                    return await func(*args, **kwargs)
                except expected_exceptions as e:
                    # Do not retry if circuit breaker is open or it's a structural error we shouldn't retry
                    if isinstance(e, (CircuitBreakerOpenError,)):
                        raise e

                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise e

                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} due to {str(e)}. Waiting {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor

        return wrapper

    return decorator
