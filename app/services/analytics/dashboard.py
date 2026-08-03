import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.ai_usage_metrics import AIUsageMetricsService
from app.services.analytics.campaign_metrics import CampaignMetricsService
from app.services.analytics.publishing_metrics import PublishingMetricsService
from app.services.analytics.workspace_metrics import WorkspaceMetricsService


class DashboardService:
    @staticmethod
    async def get_dashboard_overview(
        db: AsyncSession, workspace_id: uuid.UUID
    ) -> dict[str, Any]:
        """Aggregates all metrics for the real-time dashboard view."""
        campaign_metrics = await CampaignMetricsService.get_metrics(db, workspace_id)
        publishing_metrics = await PublishingMetricsService.get_metrics(
            db, workspace_id
        )
        ai_metrics = await AIUsageMetricsService.get_metrics(db, workspace_id)
        workspace_metrics = await WorkspaceMetricsService.get_metrics(db, workspace_id)

        return {
            "workspace_id": workspace_id,
            "date": date.today(),
            "campaign_metrics": campaign_metrics,
            "publishing_metrics": publishing_metrics,
            "ai_metrics": ai_metrics,
            "workspace_metrics": workspace_metrics,
        }
