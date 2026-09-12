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


def test_frontend_url_cors_configuration(monkeypatch):
    from fastapi import FastAPI

    from app.config.settings import settings
    from app.middleware.cors import add_cors_middleware

    assert (
        settings.FRONTEND_URL
        == "https://dmx-ai-marketing-tool-frontend-delta.vercel.app"
    )

    test_app = FastAPI()
    add_cors_middleware(test_app)

    cors_middleware = next(
        m for m in test_app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    allow_origins = cors_middleware.kwargs.get("allow_origins", [])
    assert "https://dmx-ai-marketing-tool-frontend-delta.vercel.app" in allow_origins
    assert "http://localhost:3000" in allow_origins
    assert "http://127.0.0.1:3000" in allow_origins

    # Test normalization (whitespace, trailing slash, multiple origins)
    monkeypatch.setattr(
        settings,
        "FRONTEND_URL",
        " https://test1.vercel.app/ , https://test2.vercel.app ",
    )
    test_app2 = FastAPI()
    add_cors_middleware(test_app2)
    cors_middleware2 = next(
        m for m in test_app2.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    allow_origins2 = cors_middleware2.kwargs.get("allow_origins", [])
    assert "https://test1.vercel.app" in allow_origins2
    assert "https://test2.vercel.app" in allow_origins2


@pytest.mark.asyncio
async def test_oauth_callback_redirect_to_new_frontend_domain():
    from unittest.mock import AsyncMock, patch

    from fastapi.testclient import TestClient

    from app.integrations.oauth.manager import OAuthManager
    from app.main import app

    state = OAuthManager.generate_state(
        "00000000-0000-0000-0000-000000000000", "google"
    )

    with (
        patch(
            "app.integrations.oauth.service.integration_service.connect_provider",
            new=AsyncMock(),
        ),
        patch(
            "app.integrations.sync.engine.sync_engine.execute_sync_job",
            new=AsyncMock(),
        ),
    ):
        client = TestClient(app, follow_redirects=False)
        response = client.get(
            "/api/v1/integrations/oauth/callback",
            params={"code": "mock_code", "state": state},
        )

        assert response.status_code == 307
        assert response.headers["location"] == (
            "https://dmx-ai-marketing-tool-frontend-delta.vercel.app/dashboard/integrations?status=success&connected=google"
        )
