# Integrations Flow

## Overview

The Integrations module allows a workspace to connect external providers using OAuth, securely store credentials, trigger synchronization jobs, receive provider webhooks, and manage the complete integration lifecycle.

All integration operations are workspace scoped and protected by RBAC permissions.

---

# Integration Architecture

```
Frontend
      │
      ▼
OAuth Authorization
      │
      ▼
OAuth Callback
      │
      ▼
Encrypted Connection Storage
      │
      ▼
Connector Factory
      │
      ▼
Provider Connector
      │
      ├────────► Manual Sync
      │
      └────────► Webhooks
```

---

# Supported Providers

The current backend registers the following providers:

- Slack
- Google
- Facebook
- Instagram
- LinkedIn
- Mock

Additional providers can be added by registering new connectors.

---

# Integration APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/integrations` | List active integrations |
| GET | `/integrations/oauth/{provider}/url` | Generate OAuth authorization URL |
| GET | `/integrations/oauth/callback` | Complete OAuth flow |
| POST | `/integrations/{provider}/sync` | Trigger manual sync |
| DELETE | `/integrations/{provider}` | Disconnect provider |
| POST | `/integrations/webhooks/{provider}` | Receive provider webhooks |

---

# OAuth Authorization Flow

The frontend requests an authorization URL.

Backend:

1. Generates a secure OAuth state.
2. Loads provider credentials.
3. Builds the provider authorization URL.
4. Returns:

- Authorization URL
- OAuth state

---

# OAuth Callback Flow

After successful provider authorization:

1. Backend validates OAuth state.
2. Extracts workspace information.
3. Exchanges authorization code.
4. Encrypts access token.
5. Encrypts refresh token.
6. Creates or updates the integration connection.
7. Marks the connection as CONNECTED.

---

# Connection Lifecycle

```
PENDING
     │
     ▼
CONNECTED
     │
     ▼
DISCONNECTED

ERROR

EXPIRED
```

---

# Active Connections

Listing integrations returns only active connections.

Each connection contains:

- Connection ID
- Provider
- Status
- Expiration Time

---

# Secure Token Storage

Provider tokens are never stored in plain text.

Before persistence:

- Access Token → Encrypted
- Refresh Token → Encrypted

Encryption uses Fernet with the configured encryption key.

Whenever a connector is used:

Encrypted Token

↓

Decrypt

↓

Connector

---

# Connector Registry

Every provider connector implements the common connector interface.

Connectors are instantiated dynamically through the Connector Factory.

Current registered connectors:

- Slack
- Google
- Facebook
- Instagram
- LinkedIn
- Mock

---

# Connection Update

If an integration already exists:

Backend updates:

- Tokens
- Metadata
- Expiration
- Status

Otherwise a new connection is created.

---

# Disconnect Flow

Disconnecting an integration:

1. Load connection.
2. Decrypt stored access token.
3. Create connector.
4. Attempt remote disconnect.
5. Clear stored credentials.
6. Mark status as DISCONNECTED.

Even if remote revocation fails, local cleanup still completes.

---

# Manual Sync

Manual sync is asynchronous.

Flow:

```
Trigger Sync

↓

Validate Active Connection

↓

Validate Connector Capability

↓

Create Background Job

↓

Job Worker

↓

Connector.sync()
```

The backend returns:

- Sync queued
- Job ID

---

# Webhook Flow

Incoming provider webhooks follow this flow:

```
Webhook Received

↓

Verify Signature

↓

Parse Payload

↓

Determine Workspace

↓

Dispatch Domain Event

↓

Event Bus
```

---

# Webhook Verification

Before processing:

- Provider signature is verified.
- Invalid signatures return:

```
401 Unauthorized
```

Supported verification currently exists for implemented providers.

---

# Event Dispatch

After successful verification:

The webhook payload is translated into an internal domain event.

The event is published through the platform Event Bus.

---

# Retry & Circuit Breaker

Provider communication uses:

- Retry Policy
- Circuit Breaker

These mechanisms improve resilience against temporary provider failures.

---

# Workspace Validation

Integration operations validate:

- Workspace
- Active connection
- Provider
- OAuth state (where applicable)

---

# Required Permissions

| Action | Permission |
|----------|------------|
| View Integrations | integration.read |
| Manage Integrations | integration.manage |

---

# Frontend Responsibilities

The frontend should:

- Display connected providers.
- Start OAuth flow.
- Handle OAuth callback completion.
- Trigger manual sync.
- Display sync status.
- Allow provider disconnection.
- Show connection status.
- Handle authorization failures.

---

# Integration Sequence

```
Workspace Selected
        │
        ▼
List Integrations
        │
        ▼
Connect Provider
        │
        ▼
OAuth Callback
        │
        ▼
Connected
        │
        ▼
Manual Sync
        │
        ▼
Receive Webhooks
```

---

# Current Backend Standard

The Integrations module provides OAuth-based provider connections, encrypted credential storage, connector abstraction, dynamic provider registration, asynchronous synchronization, webhook verification, event dispatching, retry protection, circuit breaker support, workspace isolation, RBAC authorization, and standardized `ApiResponse<T>` responses.