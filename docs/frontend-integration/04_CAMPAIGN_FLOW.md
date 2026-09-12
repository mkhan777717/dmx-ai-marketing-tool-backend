# Campaign Flow

## Overview

The Campaign module is used to create, manage, update, and track marketing campaigns within a workspace.

Every campaign belongs to a single workspace and is owned by the user who created it.

---

# Campaign Lifecycle

```
Create
   │
   ▼
DRAFT
   │
   ├────────────► ACTIVE
   │                 │
   │                 ├────────► PAUSED
   │                 │             │
   │                 │             └────► ACTIVE
   │                 │
   │                 ├────────► COMPLETED
   │                 │
   │                 └────────► ARCHIVED
   │
   └────────────► ARCHIVED
```

Only valid status transitions are allowed by the backend.

---

# Campaign APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/{workspace_id}/campaigns` | Create Campaign |
| GET | `/{workspace_id}/campaigns` | List Campaigns |
| GET | `/{workspace_id}/campaigns/{campaign_id}` | Campaign Details |
| PUT | `/{workspace_id}/campaigns/{campaign_id}` | Update Campaign |
| DELETE | `/{workspace_id}/campaigns/{campaign_id}` | Soft Delete Campaign |
| POST | `/{workspace_id}/campaigns/{campaign_id}/status` | Change Campaign Status |

---

# Campaign Creation

When a campaign is created:

- Owner is assigned automatically.
- Workspace is assigned automatically.
- Initial status is **DRAFT**.
- Brand Kit (if provided) is validated.
- Campaign dates are validated.

---

# Campaign List

Supports pagination.

Query Parameters:

| Parameter | Description |
|-----------|-------------|
| skip | Pagination offset |
| limit | Number of records |
| status | Filter by campaign status |
| search | Search by campaign name, description or objective |

Example:

```
GET /workspaces/{workspace_id}/campaigns?status=ACTIVE
```

```
GET /workspaces/{workspace_id}/campaigns?search=summer
```

---

# Campaign Details

Returns complete campaign information.

Response includes:

- Campaign ID
- Workspace ID
- Owner ID
- Campaign Name
- Description
- Objective
- Campaign Type
- Target Channels
- Budget
- Currency
- Start Date
- End Date
- Brand Kit
- Status
- Created At
- Updated At

---

# Campaign Update

Editable fields include:

- Campaign Name
- Description
- Objective
- Campaign Type
- Target Channels
- Budget
- Currency
- Start Date
- End Date
- Brand Kit

Backend validates:

- Date range
- Brand Kit existence

---

# Campaign Delete

Campaign deletion is implemented as a soft delete.

Deleted campaigns are not returned in normal queries.

---

# Campaign Status

Status changes use the dedicated endpoint.

Allowed transitions:

| Current | Allowed |
|----------|----------|
| DRAFT | ACTIVE, ARCHIVED |
| ACTIVE | PAUSED, COMPLETED, ARCHIVED |
| PAUSED | ACTIVE, COMPLETED, ARCHIVED |
| COMPLETED | ARCHIVED |
| ARCHIVED | None |

Invalid transitions return **400 Bad Request**.

---

# Frontend Responsibilities

- Fetch campaign list after workspace selection.
- Support pagination.
- Support search.
- Support status filtering.
- Prevent invalid date ranges.
- Refresh list after create/update/delete.
- Use the dedicated status endpoint for status changes.

---

# Required Permissions

| Action | Permission |
|---------|------------|
| Create | campaign.create |
| Read | campaign.read |
| Update | campaign.update |
| Delete | campaign.delete |

---

# Integration Sequence

```
Workspace Selected
        │
        ▼
List Campaigns
        │
        ▼
Create Campaign
        │
        ▼
Campaign Details
        │
        ▼
Update Campaign
        │
        ▼
Change Status
        │
        ▼
Delete Campaign
```

---

# Current Backend Standard

The Campaign module supports complete CRUD operations, search, pagination, status filtering, controlled lifecycle transitions, workspace isolation, RBAC authorization, and standardized `ApiResponse<T>` responses.