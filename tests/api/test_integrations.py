import asyncio

import pytest

from app.integrations.circuit_breaker.breaker import CircuitBreaker, CircuitState
from app.integrations.exceptions import CircuitBreakerOpenError, RateLimitExceededError
from app.integrations.rate_limit.limiter import RateLimiter, rate_limit
from app.integrations.secrets.adapters.environment import SecretAdapter
from app.integrations.secrets.service import SecretService


class MockAdapter(SecretAdapter):
    def get_secret(self, key: str) -> str | None:
        if key == "ENCRYPTION_KEY":
            return "K_wE8r2rV8vJd3M8yG8a1D_k8mF-M8vU9hBqJ3e9U1w="
        return f"mock_secret_for_{key}"


@pytest.mark.asyncio
async def test_circuit_breaker():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

    async def failing_func():
        raise ValueError("Simulated failure")

    async def passing_func():
        return "success"

    # First failure
    with pytest.raises(ValueError):
        await breaker.call(failing_func)
    assert breaker.state == CircuitState.CLOSED

    # Second failure opens the circuit
    with pytest.raises(ValueError):
        await breaker.call(failing_func)
    assert breaker.state == CircuitState.OPEN

    # Circuit is open, should reject immediately
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(passing_func)

    # Wait for recovery timeout
    await asyncio.sleep(1.1)
    assert breaker.state == CircuitState.HALF_OPEN

    # Success closes the circuit
    res = await breaker.call(passing_func)
    assert res == "success"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = RateLimiter(capacity=2, refill_rate=0.0)  # No refill

    @rate_limit(limiter)
    async def target():
        return True

    assert await target()
    assert await target()

    with pytest.raises(RateLimitExceededError):
        await target()


def test_secret_service_encryption():
    adapter = MockAdapter()
    service = SecretService(adapter=adapter)

    original = "my_super_secret_token"
    encrypted = service.encrypt_token(original)

    assert encrypted != original
    assert isinstance(encrypted, str)

    decrypted = service.decrypt_token(encrypted)
    assert decrypted == original
