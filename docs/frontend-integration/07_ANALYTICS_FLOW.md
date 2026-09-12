# Analytics Flow

## Overview

The Analytics module provides real-time dashboard metrics, analytics snapshots, campaign performance analytics, and AI usage statistics for each workspace.

All analytics endpoints are workspace-scoped and protected using RBAC permissions.

---

# Analytics Architecture

```
Campaigns
      │
      ▼
Publishing
      │
      ▼
AI Usage
      │
      ▼
Workspace Metrics
      │
      ▼
Dashboard Service
      │
      ├────────► Dashboard Overview
      ├────────► Analytics Snapshot
      ├────────► Campaign Analytics
      └────────► AI Usage Analytics
```

---

# Analytics APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/{workspace_id}/analytics/dashboard` | Real-time dashboard metrics |
| GET | `/{workspace_id}/analytics/overview` | Latest analytics snapshot |
| GET | `/{workspace_id}/analytics/campaigns` | Campaign analytics |
| GET | `/{workspace_id}/analytics/ai` | AI usage analytics |

---

# Dashboard Overview

Returns a real-time aggregated dashboard.

The backend combines metrics from:

- Campaign Metrics
- Publishing Metrics
- AI Usage Metrics
- Workspace Metrics

Returned response:

```
workspace_id
date
campaign_metrics
publishing_metrics
ai_metrics
workspace_metrics
```

This endpoint always returns the latest calculated metrics.

---

# Analytics Snapshot

Snapshots provide stored analytics for a specific snapshot type.

Supported snapshot types:

- DAILY
- (Other values depend on the SnapshotType enum implementation.)

When requesting a snapshot:

1. Backend checks whether a snapshot already exists.
2. If today's snapshot exists, it is returned.
3. Otherwise a new snapshot is generated automatically.
4. The snapshot is stored for future requests.

---

# Snapshot Generation

A generated snapshot contains:

- Campaign Metrics
- AI Metrics
- Publishing Metrics
- Workspace Metrics

Snapshots are reused whenever possible to avoid unnecessary recalculation.

---

# Campaign Analytics

Provides detailed analytics for campaigns.

Supports:

| Parameter | Description |
|-----------|-------------|
| skip | Pagination offset |
| limit | Maximum records |
| campaign_id | Filter by campaign |

Each campaign analytics record contains:

- Impressions
- Reach
- Clicks
- Likes
- Comments
- Shares
- Saves
- Engagement Rate

---

# AI Usage Analytics

Provides AI provider usage statistics.

Supports pagination.

Each record contains:

- Provider
- Model
- Total Generations
- Successful Generations
- Failed Generations
- Total Tokens

---

# Dashboard Metrics

The dashboard aggregates metrics from four independent services.

```
Dashboard

├── Campaign Metrics

├── Publishing Metrics

├── AI Metrics

└── Workspace Metrics
```

Frontend should render these as dashboard cards or charts.

---

# Pagination

Supported by:

- Campaign Analytics
- AI Usage Analytics

Query Parameters:

```
skip
limit
```

---

# Workspace Validation

Every analytics endpoint validates:

- Workspace exists.
- User belongs to the workspace.
- Required permission is granted.

Unauthorized requests return:

```
403 Forbidden
```

---

# Required Permissions

| Endpoint | Permission |
|----------|------------|
| Dashboard | analytics.dashboard |
| Overview | analytics.read |
| Campaign Analytics | analytics.read |
| AI Usage | analytics.read |

---

# Frontend Responsibilities

- Load dashboard after workspace selection.
- Refresh dashboard periodically if live updates are required.
- Display campaign analytics.
- Display AI usage statistics.
- Support pagination.
- Support campaign filtering.
- Display snapshot data separately from live dashboard data.

---

# Integration Sequence

```
Workspace Selected
        │
        ▼
Dashboard Overview
        │
        ▼
Analytics Snapshot
        │
        ▼
Campaign Analytics
        │
        ▼
AI Usage Analytics
```

---

# Current Backend Standard

The Analytics module provides real-time dashboard aggregation, snapshot generation, campaign performance analytics, AI usage tracking, workspace isolation, RBAC authorization, pagination support, and standardized `ApiResponse<T>` responses.