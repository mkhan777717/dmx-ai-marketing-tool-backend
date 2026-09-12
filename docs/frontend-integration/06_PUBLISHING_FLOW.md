# Publishing Flow

## Overview

The Publishing module is responsible for publishing campaign content to connected social media accounts and maintaining a complete publishing history.

Publishing is performed using the configured social provider implementation and every publish attempt is recorded.

---

# Publishing Lifecycle

```
Campaign Content
        │
        ▼
Select Social Account
        │
        ▼
Publish Request
        │
        ▼
Create Publish History (PENDING)
        │
        ▼
Execute Provider Publish
        │
   ┌────┴────┐
   ▼         ▼
SUCCESS    FAILURE
   │         │
   ▼         ▼
PUBLISHED  FAILED
```

---

# Publishing APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/{workspace_id}/publishing/publish` | Publish campaign content |
| GET | `/{workspace_id}/publishing/history` | Retrieve publishing history |

---

# Publish Flow

When the frontend requests publishing:

1. Validate the campaign content.
2. Validate the selected social account.
3. Create a **PENDING** publish history record.
4. Load the appropriate social provider.
5. Publish the content.
6. Update the publish history with the final result.

---

# Publish Request

The frontend must provide:

| Field | Required |
|--------|----------|
| content_id | Yes |
| social_account_id | Yes |

Current implementation performs immediate publishing.

Scheduling options are not currently implemented.

---

# Publish Status

Publishing history can have the following statuses:

- **PENDING**
- **PUBLISHED**
- **FAILED**

---

# Success Flow

On successful publishing the backend stores:

- Published status
- External provider post ID
- Published timestamp

---

# Failure Flow

If publishing fails:

- Status becomes **FAILED**
- Provider error message is stored
- History record remains available for review

---

# Publishing History

The backend stores every publish attempt.

Each history record includes:

- Content
- Social Account
- Publish Status
- External Post ID
- Error Message
- Published Time
- Created Time
- Updated Time

---

# History Filters

The history endpoint supports:

| Parameter | Description |
|-----------|-------------|
| skip | Pagination offset |
| limit | Maximum records |
| campaign_id | Filter by campaign |
| content_id | Filter by content |
| status | Filter by publish status |
| social_account_id | Filter by social account |

Results are ordered by newest first.

---

# Validation

Before publishing the backend verifies:

- Content exists.
- Content belongs to the selected workspace.
- Social account exists.
- Social account belongs to the selected workspace.

Invalid resources return:

```
404 Not Found
```

---

# Frontend Responsibilities

- Allow the user to select a connected social account.
- Trigger publishing.
- Display publishing progress.
- Refresh publishing history after publishing.
- Show publish status.
- Display provider error messages when publishing fails.
- Support filtering of publish history.

---

# Required Permissions

| Action | Permission |
|---------|------------|
| Publish Content | content.publish |
| View History | content.read |

---

# Integration Sequence

```
Workspace Selected
        │
        ▼
Campaign Selected
        │
        ▼
Campaign Content Selected
        │
        ▼
Select Social Account
        │
        ▼
Publish
        │
        ▼
History Updated
        │
        ▼
Display Result
```

---

# Current Backend Standard

The Publishing module validates workspace resources, records every publish attempt, delegates publishing to the configured social provider, tracks publish status, supports filtered history retrieval, and returns standardized `ApiResponse<T>` responses.