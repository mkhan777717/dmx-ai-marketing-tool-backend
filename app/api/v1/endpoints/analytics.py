import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_workspace, require_permission
from app.constants.enums import SnapshotType
from app.db.session import get_db_session
from app.repositories.analytics import ai_usage_repo, campaign_analytics_repo
from app.schemas.analytics import (AIUsageResponse, AnalyticsSnapshotResponse,
                                   CampaignAnalyticsResponse,
                                   DashboardOverviewResponse)
from app.services.analytics.core import AnalyticsService
from app.services.analytics.dashboard import DashboardService

router = APIRouter()


@router.get(
    "/{workspace_id}/analytics/dashboard",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "dashboard"))],
)
async def get_dashboard(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get the real-time aggregated dashboard overview metrics for the workspace.
    """
    return await DashboardService.get_dashboard_overview(db, workspace_id)


@router.get(
    "/{workspace_id}/analytics/overview",
    response_model=AnalyticsSnapshotResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def get_analytics_overview(
    workspace_id: uuid.UUID,
    snapshot_type: SnapshotType = Query(SnapshotType.DAILY),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get the latest analytics snapshot for the workspace.
    Generates a new snapshot if none exists for today.
    """
    return await AnalyticsService.get_latest_snapshot(db, workspace_id, snapshot_type)


@router.get(
    "/{workspace_id}/analytics/campaigns",
    response_model=Sequence[CampaignAnalyticsResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def list_campaign_analytics(
    workspace_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get detailed granular campaign analytics.
    """
    return await campaign_analytics_repo.get_by_workspace_id(
        db, workspace_id, skip, limit
    )


@router.get(
    "/{workspace_id}/analytics/ai",
    response_model=Sequence[AIUsageResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def list_ai_usage_analytics(
    workspace_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get detailed granular AI usage analytics.
    """
    return await ai_usage_repo.get_by_workspace_id(db, workspace_id, skip, limit)
