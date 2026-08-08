import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_workspace, require_permission
from app.constants.enums import SnapshotType
from app.db.session import get_db_session
from app.repositories.analytics import ai_usage_repo, campaign_analytics_repo
from app.schemas.analytics import (
    AIUsageResponse,
    AnalyticsSnapshotResponse,
    CampaignAnalyticsResponse,
    DashboardOverviewResponse,
)
from app.schemas.responses import ApiResponse
from app.services.analytics.core import AnalyticsService
from app.services.analytics.dashboard import DashboardService

router = APIRouter()


@router.get(
    "/{workspace_id}/analytics/dashboard",
    response_model=ApiResponse[DashboardOverviewResponse],
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
    dashboard = await DashboardService.get_dashboard_overview(db, workspace_id)
    return ApiResponse(
        success=True, message="Dashboard metrics retrieved", data=dashboard
    )


@router.get(
    "/{workspace_id}/analytics/overview",
    response_model=ApiResponse[AnalyticsSnapshotResponse],
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
    snapshot = await AnalyticsService.get_latest_snapshot(
        db, workspace_id, snapshot_type
    )
    return ApiResponse(
        success=True, message="Analytics overview retrieved", data=snapshot
    )


@router.get(
    "/{workspace_id}/analytics/campaigns",
    response_model=ApiResponse[Sequence[CampaignAnalyticsResponse]],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def list_campaign_analytics(
    workspace_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    campaign_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get detailed granular campaign analytics.
    """
    campaigns = await campaign_analytics_repo.get_by_workspace_id(
        db, workspace_id, skip, limit, campaign_id
    )
    return ApiResponse(
        success=True, message="Campaign analytics retrieved", data=campaigns
    )


@router.get(
    "/{workspace_id}/analytics/ai",
    response_model=ApiResponse[Sequence[AIUsageResponse]],
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
    usage = await ai_usage_repo.get_by_workspace_id(db, workspace_id, skip, limit)
    return ApiResponse(success=True, message="AI usage retrieved", data=usage)
