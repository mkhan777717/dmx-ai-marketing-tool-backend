import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_live():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_correlation_id_middleware():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Pass a custom correlation ID
        headers = {"X-Correlation-ID": "test-corr-id"}
        response = await client.get("/health/live", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "test-corr-id"
    # Ensure a request ID was injected
    assert "X-Request-ID" in response.headers
