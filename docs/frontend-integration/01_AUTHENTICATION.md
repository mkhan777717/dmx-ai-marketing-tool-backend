# Authentication

## Overview

Authentication is managed by **Supabase**.

The backend does not expose login, logout, or token refresh endpoints. The frontend is responsible for authenticating users with Supabase and sending the access token to the backend.

---

## Authentication Flow

```
User
    │
    ▼
Frontend
    │
    ▼
Supabase Authentication
    │
    ▼
Access Token (JWT)
    │
    ▼
Frontend stores token
    │
    ▼
Authorization: Bearer <JWT>
    │
    ▼
Backend verifies JWT
    │
    ▼
User resolved / created
    │
    ▼
Protected API execution
```

---

## Authorization Header

Every protected API must include:

```
Authorization: Bearer <access_token>
```

---

## Backend Authentication Process

For every authenticated request:

1. Extract Bearer token.
2. Verify JWT using the Supabase JWT secret.
3. Validate the token audience.
4. Extract user information (`sub`, `email`).
5. Look up the local user.
6. Automatically create the user if it is the first login.
7. Reject inactive users.
8. Continue request execution.

---

## Workspace Authorization

For workspace-scoped APIs:

- The user must belong to the workspace.
- Workspace owners are allowed automatically.
- Active workspace members are authorized.
- Unauthorized users receive **403 Forbidden**.

---

## Permission (RBAC)

After authentication, every protected endpoint validates permissions using Role-Based Access Control (RBAC).

Permissions follow:

```
resource.action
```

Examples:

- campaign.read
- campaign.create
- publishing.manage
- analytics.dashboard
- notifications.read

---

## Authentication Errors

| Status | Meaning |
|---------|---------|
| 401 | Invalid or expired JWT |
| 403 | User is authenticated but lacks workspace access or required permission |
| 400 | User account is inactive |

---

## Frontend Responsibilities

- Authenticate users using Supabase.
- Store the access token securely.
- Send the Bearer token with every protected request.
- Handle 401 responses by re-authenticating or refreshing the session through Supabase.
- Handle 403 responses by displaying an authorization error.

---

## Current Backend Standard

Authentication is fully delegated to **Supabase**, while the backend is responsible for JWT validation, user synchronization, workspace authorization, and permission enforcement.