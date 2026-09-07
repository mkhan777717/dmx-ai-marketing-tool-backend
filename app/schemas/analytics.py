import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.constants.enums import SnapshotType


# -- AI Usage Schemas --
class AIUsageResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    provider: str
    model: str
    generations: int
    success_count: int
    failure_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -- Campaign Analytics Schemas --
class CampaignAnalyticsResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    impressions: int
    reach: int
    clicks: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -- Snapshot & Dashboard Schemas --
class AnalyticsSnapshotResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    snapshot_type: SnapshotType
    snapshot_date: date
    campaign_metrics: Optional[dict[str, Any]] = None
    ai_metrics: Optional[dict[str, Any]] = None
    publishing_metrics: Optional[dict[str, Any]] = None
    workspace_metrics: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardOverviewResponse(BaseModel):
    workspace_id: uuid.UUID
    date: date
    campaign_metrics: dict[str, Any]
    ai_metrics: dict[str, Any]
    publishing_metrics: dict[str, Any]
    workspace_metrics: dict[str, Any]


# -- GA4 Analytics Schemas --
class GA4MetricHeader(BaseModel):
    name: str
    type: str


class GA4Row(BaseModel):
    dimension_values: list[str]
    metric_values: list[str]


class GA4ReportResponse(BaseModel):
    property_id: str
    property_name: str
    dimension_headers: list[str]
    metric_headers: list[GA4MetricHeader]
    rows: list[GA4Row]
    row_count: int


# -- Google Ads Analytics Schemas --
class GoogleAdsRow(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    impressions: int
    clicks: int
    cost_micros: int
    cost: float


class GoogleAdsReportResponse(BaseModel):
    customer_id: str
    resource_name: str
    query: str
    rows: list[GoogleAdsRow]
    row_count: int


# -- Search Console Analytics Schemas --
class SearchConsoleRow(BaseModel):
    keys: list[str]
    clicks: int
    impressions: int
    ctr: float
    position: float


class SearchConsoleReportResponse(BaseModel):
    site_url: str
    start_date: str
    end_date: str
    dimensions: list[str]
    rows: list[SearchConsoleRow]
    row_count: int
