# Notification Flow

## Overview

The Notification module provides in-app notifications for users and allows them to manage notification preferences.

Notifications are user-specific, workspace-aware, and support unread tracking, read status, deletion, and delivery preferences.

---

# Notification Lifecycle

```
System Event
      │
      ▼
Notification Created
      │
      ▼
Unread Notification
      │
      ▼
User Opens Notification
      │
      ▼
Mark as Read
      │
      ▼
Delete (Optional)
```

---

# Notification APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/notifications` | Get unread notifications |
| PATCH | `/notifications/{notification_id}/read` | Mark notification as read |
| PATCH | `/notifications/read-all` | Mark all notifications as read |
| DELETE | `/notifications/{notification_id}` | Delete notification |
| GET | `/notifications/preferences` | Get notification preferences |

---

# Notification Retrieval

The notification list returns only unread notifications.

Results are:

- Filtered by current authenticated user.
- Ordered by newest first.
- Limited using the `limit` query parameter.

Default limit:

```
50
```

---

# Notification Data

Each notification contains:

- Notification ID
- Workspace ID
- User ID
- Title
- Body
- Notification Type
- Priority
- Additional Data (optional)
- Read Timestamp
- Created Timestamp

---

# Mark as Read

When a notification is opened:

1. Backend verifies ownership.
2. Updates `read_at`.
3. Returns the updated notification.

If already marked as read, no additional update is performed.

---

# Mark All as Read

Marks every unread notification for the current user as read.

Returns the number of updated notifications.

Example:

```json
{
  "message": "12 notifications marked as read"
}
```

---

# Delete Notification

Before deletion the backend verifies:

- Notification exists.
- Notification belongs to the current user.

Deletion removes the notification record.

---

# Notification Preferences

Each notification type has configurable preferences.

Available channels:

- In-App
- Email
- Push

Each channel can be enabled or disabled independently.

---

# Preference Fields

Each preference contains:

| Field | Description |
|--------|-------------|
| notification_type | Notification category |
| in_app_enabled | Enable in-app notifications |
| email_enabled | Enable email notifications |
| push_enabled | Enable push notifications |

---

# Notification Priority

Notifications support priorities.

Current implementation uses:

- NORMAL
- HIGH

Priority can be used by the frontend for display emphasis.

---

# Notification Types

Notification types are represented by the `NotificationType` enum.

Examples depend on the backend enum implementation.

---

# Validation

For every notification operation the backend validates:

- User authentication.
- Notification ownership.
- Required permission.

Invalid requests return:

```
404 Not Found
```

or

```
403 Forbidden
```

depending on the operation.

---

# Required Permissions

| Action | Permission |
|---------|------------|
| Read Notifications | notifications.read |
| Delete Notifications | notifications.manage |

---

# Frontend Responsibilities

The frontend should:

- Display unread notification count.
- Display unread notifications.
- Mark notifications as read after opening.
- Allow "Mark All as Read".
- Allow notification deletion.
- Display notification priority.
- Provide a notification preferences screen.

---

# Integration Sequence

```
User Login
      │
      ▼
Fetch Notifications
      │
      ▼
Display Badge Count
      │
      ▼
Open Notification
      │
      ▼
Mark as Read
      │
      ▼
Delete (Optional)
      │
      ▼
Notification Preferences
```

---

# Current Backend Standard

The Notification module supports unread notification retrieval, individual and bulk read operations, notification deletion, configurable delivery preferences, ownership validation, RBAC authorization, and user-specific notification management.