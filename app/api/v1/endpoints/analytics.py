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
    GA4ReportResponse,
    GoogleAdsReportResponse,
    SearchConsoleReportResponse,
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


@router.get(
    "/{workspace_id}/analytics/ga4/report",
    response_model=ApiResponse[GA4ReportResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def get_ga4_report(
    workspace_id: uuid.UUID,
    property_id: str = Query(
        ..., description="GA4 Property ID (e.g. 987654 or properties/987654)"
    ),
    start_date: str = Query(
        "30daysAgo",
        description="Start date (YYYY-MM-DD or relative string like '30daysAgo')",
    ),
    end_date: str = Query(
        "today", description="End date (YYYY-MM-DD or relative string like 'today')"
    ),
    dimensions: list[str] | None = Query(
        None, description="Optional list of GA4 dimension names"
    ),
    metrics: list[str] | None = Query(
        None, description="Optional list of GA4 metric names"
    ),
    limit: int | None = Query(
        None, ge=1, le=10000, description="Optional row count limit"
    ),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get a custom Google Analytics 4 (GA4) runReport for a workspace's connected property.
    """
    from fastapi import HTTPException

    from app.integrations.connectors.google.analytics import GoogleAnalyticsService
    from app.integrations.oauth.models import ConnectionStatus
    from app.integrations.oauth.repository import integration_connection_repo
    from app.integrations.secrets.service import secret_service

    # 1. Retrieve existing Google IntegrationConnection for workspace
    connection = await integration_connection_repo.get_by_workspace_and_provider(
        db, workspace_id, "google"
    )
    if not connection or connection.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google integration connection not found or not connected for this workspace",
        )

    # 2. Read persisted GA4 properties from metadata_info
    metadata = connection.metadata_info or {}
    ga4_properties = metadata.get("ga4_properties", [])
    if not ga4_properties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GA4 properties discovered or configured for this workspace's Google connection",
        )

    # 3. Validate that requested property belongs to authenticated workspace's Google connection
    clean_requested_id = property_id.split("/")[-1]
    matching_property = next(
        (
            p
            for p in ga4_properties
            if p.get("property_id") == clean_requested_id
            or p.get("property_name") == property_id
        ),
        None,
    )
    if not matching_property:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requested GA4 property '{property_id}' does not belong to this workspace's Google connection",
        )

    # 4. Decrypt access token
    if not connection.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google access token missing from connection",
        )

    decrypted_token = secret_service.decrypt_token(connection.access_token)
    if not decrypted_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to decrypt Google access token",
        )

    # 5. Execute GA4 runReport via GoogleAnalyticsService
    analytics_service = GoogleAnalyticsService(decrypted_token)
    report_data = await analytics_service.get_report(
        property_id=property_id,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        metrics=metrics,
        limit=limit,
    )

    return ApiResponse(
        success=True, message="GA4 report retrieved successfully", data=report_data
    )


@router.get(
    "/{workspace_id}/analytics/google-ads/report",
    response_model=ApiResponse[GoogleAdsReportResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def get_google_ads_report(
    workspace_id: uuid.UUID,
    customer_id: str = Query(
        ...,
        description="Google Ads Customer ID (e.g. 6774894805 or customers/6774894805)",
    ),
    start_date: str = Query(
        "30daysAgo",
        description="Start date (YYYY-MM-DD or relative string like '30daysAgo')",
    ),
    end_date: str = Query(
        "today", description="End date (YYYY-MM-DD or relative string like 'today')"
    ),
    login_customer_id: str | None = Query(
        None, description="Optional Manager (MCC) Account Customer ID"
    ),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get a campaign performance report from Google Ads API v25 for a workspace's connected Google Ads customer account.
    """
    from fastapi import HTTPException

    from app.integrations.connectors.google.ads import GoogleAdsService
    from app.integrations.connectors.google.exceptions import (
        GoogleApiError,
        GoogleAuthError,
        GoogleQuotaError,
    )
    from app.integrations.oauth.models import ConnectionStatus
    from app.integrations.oauth.repository import integration_connection_repo
    from app.integrations.secrets.service import secret_service

    # 1. Retrieve existing Google IntegrationConnection for workspace
    connection = await integration_connection_repo.get_by_workspace_and_provider(
        db, workspace_id, "google"
    )
    if not connection or connection.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google integration connection not found or not connected for this workspace",
        )

    # 2. Read persisted Google Ads customers from metadata_info
    metadata = connection.metadata_info or {}
    google_ads_customers = metadata.get("google_ads_customers", [])
    if not google_ads_customers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google Ads customers discovered or configured for this workspace's Google connection",
        )

    # 3. Validate that requested customer belongs to authenticated workspace's Google connection
    clean_requested_id = customer_id.split("/")[-1].replace("-", "")
    matching_customer = next(
        (
            c
            for c in google_ads_customers
            if c.get("customer_id") == clean_requested_id
            or c.get("resource_name") == customer_id
            or c.get("customer_id") == customer_id
        ),
        None,
    )
    if not matching_customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requested Google Ads customer '{customer_id}' does not belong to this workspace's Google connection",
        )

    # 4. Decrypt access token
    if not connection.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google access token missing from connection",
        )

    decrypted_token = secret_service.decrypt_token(connection.access_token)
    if not decrypted_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to decrypt Google access token",
        )

    # 5. Execute Google Ads reporting query via GoogleAdsService
    effective_login_id = login_customer_id or matching_customer.get("login_customer_id")
    ads_service = GoogleAdsService(
        access_token=decrypted_token,
        login_customer_id=effective_login_id,
    )

    try:
        report_data = await ads_service.get_report(
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            login_customer_id=effective_login_id,
        )
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except GoogleQuotaError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except GoogleApiError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ApiResponse(
        success=True,
        message="Google Ads report retrieved successfully",
        data=report_data,
    )


@router.get(
    "/{workspace_id}/analytics/search-console/report",
    response_model=ApiResponse[SearchConsoleReportResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics", "read"))],
)
async def get_search_console_report(
    workspace_id: uuid.UUID,
    site_url: str = Query(
        ...,
        description="Google Search Console property site URL (e.g. https://example.com/ or sc-domain:example.com)",
    ),
    start_date: str = Query(
        "30daysAgo",
        description="Start date (YYYY-MM-DD or relative string like '30daysAgo')",
    ),
    end_date: str = Query(
        "today", description="End date (YYYY-MM-DD or relative string like 'today')"
    ),
    dimensions: list[str] | None = Query(
        None,
        description="Optional list of dimensions (query, page, country, device, date)",
    ),
    row_limit: int | None = Query(
        None, ge=1, le=25000, description="Optional row count limit (1 to 25000)"
    ),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get Search Analytics performance report from Google Search Console API v1 for a workspace's connected property.
    """
    from fastapi import HTTPException

    from app.integrations.connectors.google.exceptions import (
        GoogleApiError,
        GoogleAuthError,
        GoogleQuotaError,
    )
    from app.integrations.connectors.google.search_console import (
        GoogleSearchConsoleService,
    )
    from app.integrations.oauth.models import ConnectionStatus
    from app.integrations.oauth.repository import integration_connection_repo
    from app.integrations.secrets.service import secret_service

    # 1. Retrieve existing Google IntegrationConnection for workspace
    connection = await integration_connection_repo.get_by_workspace_and_provider(
        db, workspace_id, "google"
    )
    if not connection or connection.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google integration connection not found or not connected for this workspace",
        )

    # 2. Read persisted Search Console sites from metadata_info
    metadata = connection.metadata_info or {}
    sc_sites = metadata.get("search_console_sites", [])
    if not sc_sites:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Search Console sites discovered or configured for this workspace's Google connection",
        )

    # 3. Validate that requested site_url belongs to authenticated workspace's Google connection
    matching_site = next(
        (s for s in sc_sites if s.get("site_url") == site_url),
        None,
    )
    if not matching_site:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requested Search Console site '{site_url}' does not belong to this workspace's Google connection",
        )

    # 4. Decrypt access token
    if not connection.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google access token missing from connection",
        )

    decrypted_token = secret_service.decrypt_token(connection.access_token)
    if not decrypted_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to decrypt Google access token",
        )

    # 5. Execute Search Console query via GoogleSearchConsoleService
    sc_service = GoogleSearchConsoleService(access_token=decrypted_token)

    try:
        report_data = await sc_service.get_search_analytics(
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=dimensions,
            row_limit=row_limit,
        )
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except GoogleQuotaError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except GoogleApiError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ApiResponse(
        success=True,
        message="Search Console report retrieved successfully",
        data=report_data,
    )
