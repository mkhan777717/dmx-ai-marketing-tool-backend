# Campaign Content Flow

## Overview

The Campaign Content module manages AI-generated and manually created content associated with a marketing campaign.

Content is versioned, workspace-scoped, and linked to a specific campaign.

---

# Content Lifecycle

```
Generate with AI
        │
        ▼
Review
        │
        ▼
Save to Campaign
        │
        ▼
DRAFT
        │
        ▼
Update
        │
        ▼
New Version Created (if applicable)
        │
        ▼
Delete
```

---

# AI Content APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/{workspace_id}/ai/generate` | Generate AI content |
| POST | `/{workspace_id}/campaigns/{campaign_id}/contents` | Save campaign content |
| GET | `/{workspace_id}/campaigns/{campaign_id}/contents` | List campaign content |
| GET | `/{workspace_id}/campaigns/{campaign_id}/contents/{content_id}` | Get content details |
| PATCH | `/{workspace_id}/campaigns/{campaign_id}/contents/{content_id}` | Update content |
| DELETE | `/{workspace_id}/campaigns/{campaign_id}/contents/{content_id}` | Delete content |

---

# AI Content Generation

AI generation does **not** automatically save content.

Frontend sends:

- Prompt
- Content Type
- Language
- Brand Kit (optional)
- Tone of Voice (optional)
- Target Audience (optional)
- AI Provider

Backend:

- Selects the requested AI provider.
- Generates content.
- Returns generated content.
- Does **not** store it in the database.

---

# Saving Content

To save generated (or manually written) content:

1. Generate AI content (optional).
2. Allow user to review/edit.
3. Call Create Campaign Content API.
4. Backend stores the content under the selected campaign.

---

# Content Versioning

The backend supports content versioning.

When new content of the same type and language is saved:

- Current version is marked as inactive.
- Version number is incremented.
- Parent version reference is maintained.
- New content becomes the current version.

The first content starts with:

```
Version = 1
```

---

# Campaign Validation

Before saving content, the backend verifies:

- Campaign exists.
- Campaign belongs to the selected workspace.

Invalid campaigns return:

```
404 Not Found
```

---

# Content Status

Newly created content is automatically assigned:

```
DRAFT
```

Status can later be updated using the update endpoint.

---

# Content List

Supports pagination.

Query Parameters:

| Parameter | Description |
|-----------|-------------|
| skip | Pagination offset |
| limit | Maximum records |

Content is returned in descending order of creation date.

---

# Editable Fields

Frontend can update:

- Title
- Content Type
- Status
- Language
- Body
- Summary
- Hashtags
- CTA
- SEO Title
- SEO Description
- Metadata
- Scheduled Placeholder

---

# Delete Content

Deleting content removes the selected campaign content record.

Frontend should refresh the campaign content list after deletion.

---

# Required Permissions

| Action | Permission |
|---------|------------|
| Generate AI | ai.create |
| Create | content.create |
| Read | content.read |
| Update | content.update |
| Delete | content.delete |

---

# Frontend Responsibilities

- Generate AI content.
- Allow user review before saving.
- Save approved content to the campaign.
- Support pagination.
- Display current content version.
- Refresh content list after create/update/delete.
- Handle validation errors returned by the backend.

---

# Integration Sequence

```
Workspace Selected
        │
        ▼
Campaign Selected
        │
        ▼
Generate AI Content
        │
        ▼
User Review / Edit
        │
        ▼
Save Campaign Content
        │
        ▼
List Campaign Content
        │
        ▼
Update Content
        │
        ▼
Delete Content
```

---

# Current Backend Standard

The Campaign Content module supports AI-assisted content generation, version-controlled content storage, workspace isolation, campaign validation, RBAC authorization, pagination, and standardized `ApiResponse<T>` responses.