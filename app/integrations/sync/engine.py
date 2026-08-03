import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import JobPriority
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.oauth.service import integration_service
from app.jobs.queue import queue_service

logger = logging.getLogger(__name__)


class SyncEngine:
    @staticmethod
    async def trigger_sync(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
        sync_type: str = "full",
    ) -> dict[str, Any]:
        """
        Trigger a sync for a specific provider.
        Instead of executing immediately, this enqueues a background job using our Job Framework.
        """
        provider = provider.lower()
        connection = await integration_connection_repo.get_by_workspace_and_provider(
            db, workspace_id, provider
        )
        if not connection or connection.status != "CONNECTED":
            raise ValueError(f"No active connection for provider {provider}")

        # Ensure the connector supports syncing
        connector = await integration_service.get_connector_instance(connection)
        capabilities = connector.get_capabilities()
        if not capabilities.can_sync:
            raise ValueError(f"Provider {provider} does not support syncing.")

        payload = {
            "workspace_id": str(workspace_id),
            "provider": provider,
            "sync_type": sync_type,
        }

        job_id = await queue_service.enqueue(
            job_name="integration.sync", payload=payload, priority=JobPriority.HIGH
        )

        return {"status": "sync_enqueued", "job_id": str(job_id)}

    @staticmethod
    async def execute_sync_job(
        db: AsyncSession, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        The actual background execution logic called by the Job Worker.
        """
        workspace_id = uuid.UUID(payload["workspace_id"])
        provider = payload["provider"]
        sync_type = payload.get("sync_type", "full")

        connection = await integration_connection_repo.get_by_workspace_and_provider(
            db, workspace_id, provider
        )
        if not connection:
            raise Exception("Connection lost before sync could execute.")

        connector = await integration_service.get_connector_instance(connection)

        # Execute the sync via the connector abstraction
        sync_result = await connector.sync(sync_type=sync_type)
        return sync_result


sync_engine = SyncEngine()
