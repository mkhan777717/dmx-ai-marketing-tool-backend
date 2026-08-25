import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.interfaces import IntegrationCapabilities


class MockConnector(AbstractConnector):
    async def connect(
        self, auth_code: str, code_verifier: str | None = None
    ) -> dict[str, Any]:
        """Mock exchanging auth_code for tokens."""
        if auth_code == "invalid_code":
            raise ValueError("Invalid auth code")

        return {
            "access_token": f"mock_access_{uuid.uuid4().hex[:8]}",
            "refresh_token": f"mock_refresh_{uuid.uuid4().hex[:8]}",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "mock_account_id": "acc_12345",
        }

    async def disconnect(self) -> bool:
        """Mock disconnect."""
        return True

    async def validate(self) -> bool:
        """Mock validate."""
        return bool(self.access_token)

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Mock sync logic."""
        if not self.access_token:
            raise ValueError("Not connected")
        return {"status": "synced", "records": 42}

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Mock webhook processing."""
        return {"processed": True, "event_type": payload.get("type", "unknown")}

    def get_capabilities(self) -> IntegrationCapabilities:
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=True,
            supported_actions=["send_message", "read_analytics"],
        )
