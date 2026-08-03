import asyncio
import logging
from functools import wraps
from typing import Callable

from app.integrations.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


# Basic implementation. Should use Redis in production for distributed limits.
class RateLimiter:
    """
    A simple async token bucket rate limiter (in-memory).
    """

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self.lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_refill

            # Refill tokens
            new_tokens = elapsed * self.refill_rate
            if new_tokens > 0:
                self.tokens = min(self.capacity, self.tokens + new_tokens)
                self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


def rate_limit(limiter: RateLimiter):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not await limiter.acquire():
                raise RateLimitExceededError("Rate limit exceeded")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
