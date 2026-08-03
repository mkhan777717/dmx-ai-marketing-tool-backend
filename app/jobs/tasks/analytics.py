import logging
from typing import Any

from app.jobs.base import JobPayload

logger = logging.getLogger(__name__)


class AnalyticsTaskPayload(JobPayload):
    workspace_id: str


async def generate_snapshot(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to generate an analytics snapshot.
    """
    payload = AnalyticsTaskPayload(**payload_dict)
    logger.info(f"Executing generate_snapshot for Workspace {payload.workspace_id}")
    # Call AnalyticsService.generate_snapshot()
    return {"status": "success", "workspace_id": payload.workspace_id}


async def refresh_dashboard(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to refresh dashboard cache.
    """
    payload = AnalyticsTaskPayload(**payload_dict)
    logger.info(f"Executing refresh_dashboard for Workspace {payload.workspace_id}")
    # Call DashboardService.refresh()
    return {"status": "success", "workspace_id": payload.workspace_id}


async def cleanup_analytics(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to clean up old granular analytics data.
    """
    logger.info("Executing cleanup_analytics globally")
    return {"status": "success"}
