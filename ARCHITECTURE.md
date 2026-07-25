# ARCHITECTURE.md

## 1. Overview
The AI Marketing Suite is a digital marketing SaaS platform. It leverages artificial intelligence to automate, manage, and optimize marketing campaigns. The backend system provides a highly scalable, async-first API that handles multi-tenant data isolation, role-based access control, scheduling, and notifications.

## 2. Project Vision
To build a reliable, extensible, and developer-friendly AI marketing platform that empowers agencies and businesses to run optimized marketing operations. The architecture is designed to support rapid product iteration while maintaining enterprise-grade security and reliability.

## 3. Project Goals
- **Maintainability:** Clear separation of concerns utilizing the Repository Pattern and Service Layer.
- **Scalability:** Async-first approach capable of handling high concurrency, easily migratable to a microservices architecture.
- **Security:** Robust multi-tenancy, JWT-based authentication, and granular Role-Based Access Control (RBAC).
- **Testability:** High test coverage for core business logic, decoupled from database implementations.
- **Developer Experience:** Intuitive folder structure, automated migrations, and comprehensive OpenAPI documentation.

## 4. Architecture Principles
- **Clean Architecture:** Strict boundary enforcement between the API layer, business logic, and data access.
- **Dependency Injection:** Loosely coupled components via FastAPI's native dependency injection system.
- **Async-First:** End-to-end asynchronous non-blocking I/O operations (from routing down to the database driver).
- **Modular Monolith:** Domain-driven directory structure that groups related features, allowing seamless future extraction into microservices.
- **Database First, Code Second:** Schema definitions act as the single source of truth, propagated via Alembic.

## 5. Technology Stack
- **Framework:** FastAPI (Python 3.13)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy 2.x (Async Engine)
- **Database Driver:** asyncpg
- **Migrations:** Alembic
- **Validation/Serialization:** Pydantic
- **Testing:** Pytest, pytest-asyncio, anyio
- **Authentication:** Supabase Auth (JWT)
- **API Documentation:** OpenAPI / Swagger

## 6. High-Level Architecture
The system follows a Modular Monolith architecture, where all modules reside in a single deployable unit but are logically separated by domain boundaries. The application acts as a RESTful JSON API interfacing directly with a PostgreSQL instance using async queries.

## 7. System Architecture Diagram

```text
+-----------------------+
|      Client Apps      |
| (Web UI, Mobile, CLI) |
+-----------+-----------+
            | HTTP/JSON (JWT)
            v
+-----------------------+
|    FastAPI App        |
|                       |
|  +-----------------+  |
|  |     Routers     |  |
|  +--------+--------+  |
|           |           |
|  +--------+--------+  |
|  |    Services     |  |
|  +--------+--------+  |
|           |           |
|  +--------+--------+  |
|  |  Repositories   |  |
|  +--------+--------+  |
+-----------+-----------+
            | asyncpg
            v
+-----------------------+
|     PostgreSQL        |
| (Multi-tenant schema) |
+-----------------------+
```

## 8. Project Structure

The repository uses the following directory structure:

```text
dmx-ai-marketing-tool-backend/
├── app/
│   ├── api/
│   │   ├── dependencies/   # Shared API dependencies (Auth)
│   │   └── v1/             # Version 1 API
│   │       └── endpoints/  # Core API routers (health, invites, members, workspaces)
│   ├── config/             # Configuration and settings management
│   ├── constants/          # Application constants
│   ├── core/               # Core utilities (exceptions, logger)
│   ├── db/                 # Database connection and session management
│   ├── exceptions/         # Exception handlers
│   ├── middleware/         # Custom middlewares (auth, cors, logging, request_id, timing)
│   ├── models/             # SQLAlchemy ORM models
│   ├── modules/            # Feature modules
│   ├── repositories/       # Data access repositories
│   ├── schemas/            # Pydantic schemas for validation
│   ├── services/           # Business logic services
│   ├── utils/              # Helper utilities
│   └── main.py             # FastAPI application entry point
├── tests/
│   ├── api/                # Integration tests for endpoints
│   ├── core/               # Tests for core utilities
│   ├── models/             # Tests for ORM constraints & logic
│   └── services/           # Unit tests for business logic
├── alembic/                # Database migration scripts
├── pyproject.toml          # Dependency management & config
└── ARCHITECTURE.md         # Architecture documentation
```

## 9. Request Lifecycle
1. **Client Request:** HTTP request arrives at a specific FastAPI endpoint.
2. **Middleware:** Request passes through CORS, request ID, timing, and logging middlewares defined in `app/middleware/`.
3. **Dependency Resolution:** FastAPI resolves dependencies (`get_db`, `get_current_user`). JWT validation occurs here.
4. **Router (API Layer):** The router validates the incoming payload using Pydantic schemas.
5. **Service Layer:** The router delegates business logic to a specific Service class (e.g., `WorkspaceService`).
6. **Repository Layer:** The Service class calls the injected Repository (e.g., `workspace_repo`) to fetch or mutate data.
7. **Database:** The Repository executes asynchronous SQLAlchemy queries against PostgreSQL.
8. **Response:** Data propagates back up, is serialized into a Pydantic response schema, and returned to the client.

## 10. Layered Architecture
- **API (Routers):** Handles HTTP specifics—status codes, path variables, query parameters, and payload serialization. No business logic resides here.
- **Dependencies:** Reusable callables that provide contextual data (e.g., active database session, authenticated user context, permission checks).
- **Services:** Contains pure business logic. Validates domain rules, orchestrates multiple repositories, and coordinates external services.
- **Repositories:** Abstracts database interactions. Converts SQLAlchemy ORM objects into generic returns and hides complex SQL queries from the Service layer.
- **Models:** Defines the database tables, relationships, and constraints using SQLAlchemy declarative bases.
- **Database:** PostgreSQL configured with asyncpg for non-blocking operations.

## 11. Dependency Injection Strategy
The project heavily utilizes FastAPI’s `Depends()`. 
- **Database Sessions:** `get_db` (from `app.api.dependencies.db`) yields an `AsyncSession` which is bound to the current request lifecycle.
- **Services/Repositories:** Repositories are instantiated as singletons or injected into services. Services receive database sessions directly from the endpoint payload to maintain transaction context.
- **Authentication:** `get_current_user` extracts the JWT, validates it, and queries the database for the user, injecting a `User` model into the endpoint.

## 12. Configuration Management
Environment variables are managed using Pydantic's `BaseSettings` defined in `app/config/settings.py`. 
Configurations encompass:
- Application Metadata (Name, Version)
- Database credentials and async connection URIs
- JWT/Supabase keys and secrets
- Environment designation

## 13. Database Architecture
PostgreSQL is used as a relational data store. 
- **Multi-Tenancy:** Handled logically via `workspace_id` foreign keys on tenant-scoped tables. Data isolation is strictly enforced at the Repository and Service levels.
- **Soft Deletes:** Standardized via a `deleted_at` timestamp using `app.models.mixins`. Records are rarely hard-deleted to preserve referential integrity and audit trails.
- **Audit Trails:** JSONB columns and timestamp mixins track lifecycle changes (`created_at`, `updated_at`).

## 14. SQLAlchemy Architecture
Utilizes SQLAlchemy 2.0 with the Asyncio extension.
- **Declarative Base:** All models inherit from a common base (`app.models.base.Base`) containing shared mixins (e.g., UUID primary keys, audit timestamps).
- **Session Management:** `AsyncSession` is utilized exclusively. The session is scoped to the request, committed if successful, or rolled back on exception.
- **Lazy Loading Strategy:** Explicit `selectinload` or `joinedload` are used to prevent synchronous lazy-loading errors in the async context.

## 15. Alembic Migration Strategy
Alembic manages database schema versioning.
- **Auto-generation:** Migrations are auto-generated by comparing SQLAlchemy models to the database schema.
- **Async Setup:** `env.py` is configured with an async engine to apply migrations asynchronously, preventing event-loop conflicts.
- **Immutability:** Once a migration is merged into the main branch, it is strictly immutable. Fixes require new revisions.

## 16. Repository Pattern
Implemented via a generic `BaseRepository` in `app/repositories/base.py`.
- **CRUD Abstraction:** Provides standardized `get_by_id`, `get_all`, `create`, `update`, and `delete` (or soft delete) methods.
- **Specialization:** Domain-specific repositories (e.g., `WorkspaceRepository`) extend the base class to add complex querying logic (e.g., fetching members with specific roles).
- **Testing:** Repositories abstract the SQL dialect, allowing the Service layer to be thoroughly tested.

## 17. Service Layer
The brain of the application.
- **Orchestration:** Handles cross-domain concerns (e.g., creating a Workspace also creates an initial Owner role assignment).
- **Validation:** Enforces business constraints (e.g., preventing duplicate invites).
- **Error Handling:** Raises specific domain exceptions (e.g., HTTPExceptions) that the API layer translates to HTTP status codes.

## 18. API Layer
Defined in `app/api/v1/endpoints/` and `app/api/v1/`.
- **Versioning:** All endpoints are versioned (e.g., `/api/v1/workspaces`).
- **Standardization:** Strict adherence to REST principles.
- **Response Models:** All routes declare specific Pydantic `response_model` types for automated OpenAPI spec generation and data filtering.

## 19. Authentication Architecture
- **Supabase Integration:** Supabase manages identity, password reset flows, and JWT issuance.
- **JWT Verification:** `app/services/supabase_auth.py` validates the Supabase JWT using the provided parameters, extracting the `sub` claim.
- **User Syncing:** Upon successful token verification, the backend ensures the user exists in the local PostgreSQL database, creating a record on first login.
- **Dependencies:** `get_current_user` extracts identity and ensures the user is active.

## 20. Authorization (RBAC)
Role-Based Access Control is enforced hierarchically.
- **Roles:** Defined systematically (e.g., Owner, Admin, Member, Viewer) via `app.models.role.py`.
- **Permissions:** Granular string identifiers via `app.models.permission.py`.
- **Role Assignments:** Users are assigned roles within the context of a specific Workspace.
- **Permission Checks:** Endpoints utilize dependencies which query the active user's roles in the target workspace and validate against required permission scopes via `app/repositories/rbac.py`.

## 21. Workspace Architecture
The core bounded context for multi-tenancy (`app/services/workspace.py`).
- **Lifecycle:** Creation establishes the workspace and assigns the creator as the Owner.
- **Soft Delete:** Workspaces are softly deleted, instantly revoking access without dropping related historical data.
- **Ownership Transfer:** Specialized business logic handles safely migrating the unique Owner role from one member to another.

## 22. Member Management
Handled by `app/services/workspace_member.py` and `workspace_invitation.py`.
- **Invitation Flow:** Users are invited via email. The system prevents duplicate active invites.
- **Member Flow:** Upon acceptance, invites are converted to WorkspaceMembers with assigned roles.
- **Role Assignment:** Admins can alter roles preventing elevation above their own clearance.

## 23. Campaign Scheduler
Handles asynchronous campaign lifecycles via `app/services/campaign_scheduler.py`.
- **API Control:** Endpoints exist to schedule, pause, and resume campaigns (`/api/v1/campaign_schedule`).
- **Implementation:** Validates scheduling timeframes, applies states (e.g., `SCHEDULED`, `PAUSED`), and prepares data for execution.

## 24. Notification Architecture
- **Tracking:** Notifications are stored in the database (`app.models.notification.py`) with contextual JSONB metadata.
- **Service:** `app/services/notification_service.py` handles user alerts and systemic messaging.

## 25. Current Database Models
Located in `app/models/`:
- **api_key.py:** Handles tenant API keys.
- **asset.py:** Manages marketing assets.
- **audit_log.py:** JSONB-based audit tracking.
- **base.py:** The SQLAlchemy declarative base.
- **brand_kit.py:** Tenant brand configuration.
- **campaign.py:** Campaign metadata.
- **campaign_content.py:** Generated campaign content.
- **campaign_schedule.py:** Campaign timing configurations.
- **mixins.py:** Common model mixins (UUID, Timestamps, Soft Deletes).
- **notification.py:** User alerts and system notifications.
- **permission.py:** String-based granular permissions.
- **plan.py:** Subscription plan definitions.
- **role.py:** RBAC roles.
- **role_permission.py:** Association between roles and permissions.
- **user.py:** Represents an authenticated identity. Tracks `supabase_user_id`.
- **user_preference.py:** JSONB configuration for user-specific settings.
- **workspace.py:** The tenant boundary. Includes slug, name, and status.
- **workspace_invite.py:** Tracks pending workspace invitations.
- **workspace_member.py:** Association table connecting Users to Workspaces.

## 26. Current Repositories
Located in `app/repositories/`:
- **api_key.py:** Manages API Keys.
- **audit_log.py:** Tracks audit trails.
- **base.py:** Generic BaseRepository for all core CRUD operations.
- **campaign_schedule.py:** Handles campaign states and scheduling data.
- **notification.py:** Handles user notifications.
- **plan.py:** Plan and subscription data access.
- **rbac.py:** Fetches role configurations and permission mappings.
- **user.py:** Manages User records.
- **user_preference.py:** Manages UserPreference data.
- **workspace.py:** Handles Workspace CRUD and isolation checks.
- **workspace_invite.py:** Handles invitation tokens and lifecycle.
- **workspace_member.py:** Manages WorkspaceMembers and membership uniqueness.

## 27. Current Services
Located in `app/services/`:
- **campaign_scheduler.py:** Validates cron expressions and manages state transitions.
- **email.py:** Handles email dispatching.
- **notification_service.py:** Manages in-app notifications.
- **supabase_auth.py:** Syncs Supabase identities to local users and verifies JWTs.
- **workspace.py:** Orchestrates workspace creation, soft deletion, and ownership transfers.
- **workspace_invitation.py:** Validates emails, generates tokens, and processes acceptances.
- **workspace_member.py:** Enforces RBAC during role assignments and handles member suspension.

## 28. Current API Modules
Located in `app/api/v1/endpoints/` and `app/api/v1/`:
- **health.py:** Basic system health check.
- **invites.py:** Invitation generation and processing.
- **members.py:** Member listing, role alterations, and removal.
- **workspaces.py:** Workspace CRUD and ownership transitions.
- **campaign_schedule.py:** Campaign timing and state management.

## 29. Error Handling Strategy
- **Domain Exceptions:** Centralized exception handling managed via `app/exceptions/handlers.py`.
- **Validation Errors:** Pydantic `ValidationError` is intercepted and formatted cleanly for the client.

## 30. Logging Strategy
- Utilizes the native `logging` library configured via `app/core/logging_config.py` and `app/core/logger.py`.
- Structured logging is utilized across middleware via `app/middleware/logging.py`.
- SQLAlchemy is configured to log emitted queries only in `DEBUG` mode.

## 31. Testing Strategy
- **Framework:** `pytest` with `pytest-asyncio`.
- **Isolation:** Each test interacts with an isolated transaction that rolls back upon completion (`AsyncSession` rollback), preventing test pollution.
- **Coverage:** The backend maintains a comprehensive automated test suite testing repositories, models, services, and API endpoints.
- **Current Status:** At the time of writing, 32 automated tests are passing successfully.

## 32. Security Considerations
- **CORS:** Scope-limited origin headers configured via `app/middleware/cors.py`.
- **SQL Injection:** Mitigated entirely by SQLAlchemy ORM parameterized queries.
- **Data Leaks:** Multi-tenancy logic is injected at the deepest repository level, preventing accidental cross-tenant data exposure.

## 33. Performance Considerations
- **Async I/O:** Using `asyncpg` ensures the thread pool is not blocked during database round trips.
- **Indexes:** Explicit indexing on high-cardinality search columns (`workspace_id`, `user_id`, `deleted_at`).
- **JSONB:** Used pragmatically for schemaless data (preferences, audit logs) to prevent excessive JOINs.

## 34. Scalability Strategy
**Modular Monolith Selection:**
A modular monolith was explicitly chosen for the current stage to maximize developer velocity, simplify deployments, and ensure transactional integrity across domains. 

**Microservices Migration Path:**
The strict enforcement of the Service and Repository layers guarantees that domain boundaries are respected. When scaling demands it, these isolated modules can be lifted into distinct FastAPI services with minimal refactoring.

## 35. Future Roadmap
### Short Term
- Implementation of the AI Content Generation module.
- Redis-based caching layer for RBAC permission checks.
- Comprehensive API rate limiting middleware.

### Medium Term
- Background worker integration (e.g., Celery or ARQ) for async email delivery and long-running AI tasks.
- Advanced analytics and reporting aggregates.
- Webhook dispatch system for tenant events.

### Long Term
- Extraction of the Campaign execution engine into a dedicated high-throughput microservice.
- Global CDN integration for generated asset delivery.
- Production deployment infrastructure utilizing Docker and Kubernetes/AWS.

## 36. Deployment Architecture
*Note: Currently marked as Future Enhancement.*
- High Availability setups, Docker containerization, CDN networks, and load-balanced architectures are planned for the production rollout but are not yet implemented in the repository.

## 37. Coding Standards
- **Formatting:** Standardized PEP 8 compliance.
- **Type Hints:** Required for all new functions and methods.
- **Modularization:** No inline complex queries within endpoints.

## 38. Git Workflow
- Standard Feature Branch workflow.
- Commit messages adhere to clear, descriptive statements.

## 39. Branch Strategy
- `main`: Represents the active development and stable state of the application.
- `feature/*`: Scoped feature development branches branching off `main`.

## 40. Current Implementation Status
- **Implemented:** FastAPI Base, Database Config, Alembic, RBAC, Workspaces, Invites, Member Management, Campaign Scheduling (API), Soft Deletes, Pytest Suite (32 tests passing).
- **In Progress:** None.
- **Planned:** AI Agent Integration, Background Task Workers, Redis Caching, Production Deployment Infrastructure.

## 41. Known Technical Debt
- Permissions are currently fetched from the database on every protected request. A caching layer is needed as a future enhancement.

## 42. Future Improvements
- Implement GraphQL or sparse fieldsets for bandwidth-heavy endpoints.
- Enhance JSONB audit logging with standardized schema validation.

## 43. Architecture Decision Records
- **ADR-001 (Async ORM):** Chose SQLAlchemy 2.0 Async over TortoiseORM for ecosystem maturity.
- **ADR-002 (RBAC Design):** Chose a Workspace-scoped RBAC over Global RBAC to allow users to hold different permissions across multiple tenants.
- **ADR-003 (UUIDs):** Adopted UUIDv4 for all primary keys to prevent enumeration attacks and facilitate future data merging.

## 44. Glossary
- **Tenant:** A distinct organization operating within the platform, represented by a Workspace.
- **JWT:** JSON Web Token, utilized for stateless authentication via Supabase.
- **RBAC:** Role-Based Access Control.
- **Soft Delete:** Hiding a record using a `deleted_at` timestamp instead of physically removing it via `DELETE`.

## 45. Document Information
- **Version:** 1.0.0
- **Status:** Finalized (Implementation Verified)
- **Last Updated:** 2026-07-25