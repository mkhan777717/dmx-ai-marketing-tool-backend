# Frontend Integration Checklist

## Overview

This document serves as the final integration guide for the AI Marketing Suite frontend.

It summarizes the complete frontend integration sequence, required API conventions, authentication flow, module initialization order, error handling expectations, and production readiness checklist.

This document should be used together with:

- 01_AUTHENTICATION.md
- 02_WORKSPACE_FLOW.md
- 03_API_RESPONSE_FORMAT.md
- 04_CAMPAIGN_FLOW.md
- 05_CAMPAIGN_CONTENT_FLOW.md
- 06_PUBLISHING_FLOW.md
- 07_ANALYTICS_FLOW.md
- 08_NOTIFICATION_FLOW.md
- 09_INTEGRATIONS_FLOW.md

---

# Backend Base URL

Configure the frontend using the backend API base URL.

Example

```
https://api.example.com/api/v1
```

Never hardcode URLs inside components.

Use environment variables.

Example

```
VITE_API_BASE_URL=
```

or

```
NEXT_PUBLIC_API_BASE_URL=
```

depending on the frontend framework.

---

# Authentication Flow

Frontend authentication sequence:

```
User Login

↓

Supabase Authentication

↓

Receive JWT

↓

Store JWT

↓

Attach JWT to Every Request

↓

Access Protected APIs
```

The backend does **not** provide login/logout endpoints.

Authentication is handled by Supabase.

---

# Required Request Headers

Every protected request must include:

```http
Authorization: Bearer <JWT>

Content-Type: application/json
```

Missing Authorization header results in:

```
401 Unauthorized
```

---

# Application Startup Flow

```
Application Starts

↓

Check Authentication

↓

User Logged In?

↓

YES

↓

Load Workspaces

↓

User Selects Workspace

↓

Store workspace_id

↓

Load Dashboard

↓

Application Ready
```

---

# Workspace Initialization

Immediately after authentication:

```
GET /workspaces
```

Display available workspaces.

After selection:

Store

```
workspace_id
```

All workspace-scoped endpoints require this identifier.

---

# Global Application State

The frontend should maintain:

```
Current User

Current Workspace

JWT Token

Dashboard Data

Campaign List

Notifications

Connected Integrations
```

Implementation is framework independent.

Any state manager may be used.

---

# Module Integration Order

Recommended order:

```
Authentication

↓

Workspace

↓

Dashboard

↓

Campaigns

↓

Campaign Content

↓

Publishing

↓

Analytics

↓

Notifications

↓

Integrations
```

Avoid loading dependent modules before workspace selection.

---

# Standard API Response

Most endpoints return:

```json
{
  "success": true,
  "message": "Operation completed",
  "data": {}
}
```

Frontend should always check:

```
success
```

before using

```
data
```

Display

```
message
```

when appropriate.

---

# Pagination

Supported endpoints use:

```
skip

limit
```

Example:

```
GET /campaigns?skip=0&limit=20
```

When requesting additional data:

Increase

```
skip
```

Keep

```
limit
```

consistent with the UI.

---

# Filtering

Supported filters vary by module.

Examples include:

Campaigns

```
status

search
```

Publishing

```
campaign_id

content_id

status

social_account_id
```

Analytics

```
campaign_id
```

Frontend should only send filters required for the current screen.

---

# Loading States

Every request should display a loading indicator.

Examples:

- Initial page loading
- Refreshing dashboard
- Publishing content
- Generating AI content
- Loading analytics

Avoid blocking the entire application unless necessary.

---

# Empty States

Provide friendly UI when no data exists.

Examples:

No Workspaces

No Campaigns

No Content

No Notifications

No Analytics

No Integrations

Do not display empty tables.

---

# Authentication Errors

### 401 Unauthorized

Meaning:

- Missing JWT
- Invalid JWT
- Expired JWT

Frontend action:

- Clear session
- Redirect to login

---

### 403 Forbidden

Meaning:

User lacks required permission.

Frontend action:

Display permission error.

Do not retry automatically.

---

### 404 Not Found

Meaning:

Requested resource does not exist.

Frontend action:

Display not found message.

---

### 422 Validation Error

Meaning:

Invalid request payload.

Frontend action:

Display field validation errors.

---

### 500 Internal Server Error

Meaning:

Unexpected backend error.

Frontend action:

Show generic error message.

Allow retry.

---

# Dashboard Initialization

After workspace selection:

Load:

```
Dashboard

↓

Analytics Overview

↓

Campaign Analytics

↓

AI Usage
```

Dashboard should refresh after operations that change metrics.

---

# Campaign Flow

Typical sequence:

```
List Campaigns

↓

Create Campaign

↓

Edit Campaign

↓

Change Status

↓

Delete Campaign
```

Refresh list after successful mutation.

---

# Campaign Content Flow

```
Generate AI Content

↓

Save Content

↓

Edit Content

↓

Delete Content
```

Refresh campaign content after create/update/delete.

---

# Publishing Flow

```
Select Content

↓

Select Social Account

↓

Publish

↓

Refresh Publish History
```

Show publish status clearly.

Display provider errors when publishing fails.

---

# Analytics Flow

Recommended sequence:

```
Dashboard

↓

Analytics Snapshot

↓

Campaign Analytics

↓

AI Usage
```

Support pagination where applicable.

---

# Notification Flow

Application startup:

```
Fetch Notifications

↓

Show Badge Count

↓

Display Notification List
```

When user opens a notification:

```
Mark As Read
```

Support:

- Mark All Read
- Delete Notification

---

# Integrations Flow

```
List Integrations

↓

Connect Provider

↓

OAuth Callback

↓

Refresh Connection List

↓

Manual Sync

↓

Disconnect
```

Display provider connection status.

---

# API Refresh Recommendations

Refresh data after:

Campaign Created

Campaign Updated

Campaign Deleted

Content Saved

Content Updated

Content Deleted

Publish Completed

Notification Read

Integration Connected

Integration Disconnected

Workspace Updated

---

# Security Checklist

Never:

Store JWT inside source code.

Log JWT.

Log Access Tokens.

Log Refresh Tokens.

Expose Provider Credentials.

Hardcode Workspace IDs.

Disable HTTPS in production.

---

# Frontend Responsibilities

The frontend is responsible for:

- Authentication
- Token Storage
- Workspace Selection
- Request Headers
- Error Handling
- Pagination
- Loading States
- Empty States
- User Feedback
- OAuth Redirect Handling

---

# Integration Checklist

## Authentication

- [ ] User can login
- [ ] JWT stored securely
- [ ] Authorization header attached
- [ ] Logout clears session

---

## Workspace

- [ ] Workspace list loads
- [ ] Workspace selection works
- [ ] Current workspace stored
- [ ] Workspace switching refreshes data

---

## Dashboard

- [ ] Dashboard loads
- [ ] Analytics overview loads
- [ ] Metrics display correctly

---

## Campaigns

- [ ] List campaigns
- [ ] Create campaign
- [ ] Update campaign
- [ ] Change campaign status
- [ ] Delete campaign
- [ ] Search campaigns
- [ ] Filter by status

---

## Campaign Content

- [ ] Generate AI content
- [ ] Save content
- [ ] Edit content
- [ ] Delete content
- [ ] List content

---

## Publishing

- [ ] Publish content
- [ ] Publish history loads
- [ ] Publish filters work

---

## Analytics

- [ ] Dashboard metrics
- [ ] Snapshot
- [ ] Campaign analytics
- [ ] AI usage

---

## Notifications

- [ ] Notification list
- [ ] Mark read
- [ ] Mark all read
- [ ] Delete notification
- [ ] Preferences

---

## Integrations

- [ ] OAuth URL
- [ ] OAuth callback
- [ ] List integrations
- [ ] Manual sync
- [ ] Disconnect provider

---

# Production Readiness Checklist

Before deployment verify:

- [ ] Production API URL configured
- [ ] HTTPS enabled
- [ ] Environment variables configured
- [ ] OAuth Redirect URI configured
- [ ] Error logging enabled
- [ ] Loading states implemented
- [ ] Empty states implemented
- [ ] Permission errors handled
- [ ] Validation errors handled
- [ ] Unauthorized redirects implemented

---

# Common Integration Mistakes

Avoid:

❌ Calling workspace APIs before authentication

❌ Calling protected APIs without JWT

❌ Ignoring `success` in ApiResponse

❌ Assuming every endpoint returns the same data structure

❌ Hardcoding workspace IDs

❌ Ignoring pagination

❌ Ignoring filters

❌ Not refreshing UI after mutations

❌ Displaying raw backend errors directly to users

❌ Storing sensitive tokens insecurely

---

# Complete Integration Flow

```
Application Start
        │
        ▼
Authentication
        │
        ▼
Receive JWT
        │
        ▼
Load Workspaces
        │
        ▼
Workspace Selected
        │
        ▼
Dashboard
        │
        ▼
Campaign Management
        │
        ▼
Campaign Content
        │
        ▼
Publishing
        │
        ▼
Analytics
        │
        ▼
Notifications
        │
        ▼
Integrations
        │
        ▼
Application Fully Operational
```

---

# Documentation Reference

Frontend developers should refer to the following documents during implementation:

- 01_AUTHENTICATION.md
- 02_WORKSPACE_FLOW.md
- 03_API_RESPONSE_FORMAT.md
- 04_CAMPAIGN_FLOW.md
- 05_CAMPAIGN_CONTENT_FLOW.md
- 06_PUBLISHING_FLOW.md
- 07_ANALYTICS_FLOW.md
- 08_NOTIFICATION_FLOW.md
- 09_INTEGRATIONS_FLOW.md

---

# Current Backend Standard

The AI Marketing Suite backend follows a workspace-based architecture with Supabase authentication, RBAC authorization, standardized API responses, encrypted integration credentials, asynchronous processing for supported operations, and REST APIs designed for frontend-first integration.