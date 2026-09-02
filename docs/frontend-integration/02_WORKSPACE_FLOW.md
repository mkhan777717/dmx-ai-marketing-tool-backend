# Workspace Flow

## Overview

The workspace is the primary tenant boundary of the application. Every protected business module (Campaigns, AI Content, Publishing, Analytics, Notifications, etc.) operates within a workspace context.

A user can own multiple workspaces and can also be a member of multiple workspaces.

---

# Workspace Lifecycle

```
User Login
      │
      ▼
Get User Workspaces
      │
      ▼
Select Workspace
      │
      ▼
Store workspace_id
      │
      ▼
Pass workspace_id in all workspace-scoped APIs
```

---

# Workspace APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/workspaces` | Create a workspace |
| GET | `/workspaces` | List user's workspaces |
| GET | `/workspaces/{workspace_id}` | Get workspace details |
| PATCH | `/workspaces/{workspace_id}` | Update workspace |
| DELETE | `/workspaces/{workspace_id}` | Soft delete workspace |
| POST | `/workspaces/{workspace_id}/transfer-ownership` | Transfer workspace ownership |

---

# Workspace Creation Flow

When a workspace is created, the backend automatically:

- Generates a unique slug (if not provided).
- Validates slug uniqueness.
- Creates the workspace.
- Assigns the creator as the **Owner**.
- Adds the creator as an **ACTIVE workspace member**.
- Creates an audit log entry.

---

# Workspace Selection Flow

After login:

1. Call:

```
GET /workspaces
```

2. Display all available workspaces.

3. User selects one workspace.

4. Save:

```
workspace_id
```

5. Use the selected workspace for all subsequent workspace-scoped API requests.

---

# Workspace Authorization

Every workspace request validates:

- Workspace exists.
- User is the owner or an active workspace member.
- Required RBAC permission is available.

Unauthorized requests return:

```
403 Forbidden
```

---

# Ownership Transfer

Ownership transfer is handled only through the dedicated endpoint.

Standard workspace updates cannot modify the owner.

During ownership transfer the backend:

- Validates current owner.
- Validates the new owner is an active member.
- Updates workspace ownership.
- Updates workspace roles.
- Creates an audit log.
- Sends a notification to the new owner.

---

# Workspace Update

Workspace updates support general workspace information only.

Ownership changes are **not** allowed through the update endpoint.

---

# Workspace Delete

Only the workspace owner can delete a workspace.

Deletion is implemented as a **soft delete**.

The backend also creates an audit log entry.

---

# Frontend Responsibilities

- Fetch the user's workspaces after authentication.
- Allow workspace selection.
- Store the selected `workspace_id`.
- Include the selected workspace ID in all workspace-scoped API requests.
- Handle `403 Forbidden` responses appropriately.
- Refresh the workspace list after creating a new workspace.

---

# Current Backend Standard

Workspace access is protected using authentication, workspace membership validation, and RBAC permissions. Ownership management is handled through dedicated APIs to maintain security and consistency.