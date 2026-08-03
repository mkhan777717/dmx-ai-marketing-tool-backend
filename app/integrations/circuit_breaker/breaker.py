import asyncio
import logging
import time
from typing import Any, Callable, TypeVar

from app.integrations.exceptions import CircuitBreakerOpenError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    In-memory Circuit Breaker.
    For a distributed environment, this state should ideally be stored in Redis.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,),
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> str:
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed to transition to HALF_OPEN
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if (
            self._state == CircuitState.HALF_OPEN
            or self._failure_count >= self.failure_threshold
        ):
            self._state = CircuitState.OPEN
            logger.warning(f"CircuitBreaker OPENED. Failures: {self._failure_count}")

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            logger.info("CircuitBreaker CLOSED. System recovered.")
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        current_state = self.state
        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Try again after {self.recovery_timeout} seconds."
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as e:
            self.record_failure()
            raise e


# Example global registry for circuit breakers per provider
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker()
    return _circuit_breakers[provider]
