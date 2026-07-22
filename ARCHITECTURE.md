# AI Marketing Suite - Backend Architecture

## Overview

This document defines the backend architecture for the **AI Marketing Suite**, an AI-powered Digital Marketing SaaS platform.

The backend is designed with scalability, maintainability, and modularity as core principles. The project follows a **Modular Monolith Architecture**, allowing rapid MVP development while keeping the system flexible enough to evolve into a microservices architecture when required.

This document reflects the current implementation status and serves as the primary architectural reference for backend development.

---

# Project Goals

- Build a scalable AI-powered Digital Marketing SaaS platform.
- Support multi-tenancy for organizations and agencies.
- Maintain clean, modular, and extensible architecture.
- Enable future AI service integrations.
- Keep business logic separated from infrastructure.
- Support seamless migration from MVP to enterprise-scale architecture.

---

# Architecture Decision

The backend follows a **Modular Monolith Architecture**.

### Benefits

- Faster MVP development
- Easier collaboration across developers
- Simpler deployment and maintenance
- Lower infrastructure complexity
- Clear module boundaries
- Easier debugging
- Future migration to microservices when required

---

# Technology Stack

| Component | Technology |
|------------|------------|
| Framework | FastAPI |
| Language | Python 3.13 |
| Package Manager | pip |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x (Async ORM) |
| Database Driver | asyncpg |
| API Style | REST |
| Testing | pytest + pytest-asyncio |
| Version Control | Git |
| Architecture | Modular Monolith |

### Current Implementation

- FastAPI application
- Async SQLAlchemy ORM
- Async database sessions
- Repository Pattern
- Modular project structure
- Multi-tenant model foundation
- Repository-based database access

### Planned Integrations

- Supabase Authentication
- JWT Authentication
- RBAC (Role-Based Access Control)
- Alembic Database Migrations
- Redis
- Docker
- Background Workers
- AI Providers

---

# Git Branch Strategy

```
main
│
└── dev
     │
     ├── feature/project-setup
     ├── feature/auth
     ├── feature/users
     ├── feature/organization
     ├── feature/campaign
     ├── feature/social
     ├── feature/analytics
     ├── feature/ai
     ├── feature/billing
     └── feature/*
```

## Branch Purpose

### main

- Production-ready code.

### dev

- Integration branch for completed features.

### feature/*

- Individual feature development.
- Every feature or module should be developed in its own branch.
- Pull Requests should target the `dev` branch.

---

# Project Structure

```
backend/
│
├── app/
│   ├── api/
│   │   └── v1/
│   │
│   ├── constants/
│   │
│   ├── core/
│   │
│   ├── db/
│   │
│   ├── models/
│   │
│   ├── repositories/
│   │
│   ├── services/
│   │
│   ├── middleware/
│   │
│   ├── exceptions/
│   │
│   ├── utils/
│   │
│   └── main.py
│
├── tests/
│
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

---

# Layered Architecture

The backend follows a layered architecture to ensure proper separation of responsibilities.

```
API Layer
     │
     ▼
Service Layer
     │
     ▼
Repository Layer
     │
     ▼
SQLAlchemy Async ORM
     │
     ▼
PostgreSQL
```

### API Layer

Responsible for:

- HTTP endpoints
- Request validation
- Response serialization
- Authentication & authorization
- Dependency injection

### Service Layer

Responsible for:

- Business logic
- Workflow orchestration
- Integrating multiple repositories
- Calling AI providers
- Scheduling background tasks

### Repository Layer

Responsible for:

- Database operations
- CRUD functionality
- Query abstraction
- Data access isolation

Business logic should **not** be implemented inside repositories.

### Database Layer

Responsible for:

- Async SQLAlchemy models
- Async sessions
- Entity relationships
- Database transactions

---

# Multi-Tenant Architecture

The platform is designed as a multi-tenant SaaS application.

Tenant-aware models inherit from a shared `TenantMixin`, which provides the common tenant identifier.

Current tenant identifier:

```
organization_id
```

This enables:

- Organization-level data isolation
- Shared infrastructure
- Future support for agencies managing multiple organizations

---

# Planned Modules

The backend is divided into feature-based modules.

Current and planned modules include:

- Authentication
- Organizations
- Users
- Campaign Management
- Campaign Scheduler
- Social Media
- Notifications
- Analytics
- CRM
- SEO
- Email Marketing
- AI Assistant
- Billing
- Admin

Each module should encapsulate its own business logic and remain loosely coupled with other modules.

---

# API Versioning

API endpoints are versioned from the beginning.

Example:

```
/api/v1/auth/login

/api/v1/users

/api/v1/campaigns
```

Future API versions can be introduced without breaking existing clients.

---

# Repository Pattern

The project follows the Repository Pattern.

Responsibilities include:

- CRUD operations
- Query abstraction
- Async database interaction
- Transaction management

Current repositories include:

- API Key Repository
- Audit Log Repository
- Campaign Schedule Repository
- Notification Repository
- Plan Repository
- User Preference Repository

Additional repositories will be added as new modules are implemented.

---

# Database Design Principles

- Use UUIDs as primary keys.
- Prefer SQLAlchemy Async ORM.
- Use explicit relationships.
- Keep models lightweight.
- Move database logic into repositories.
- Use migrations for schema evolution.
- Maintain tenant isolation using `organization_id`.

---

# Development Principles

- Follow clean architecture principles.
- Keep business logic separate from API routes.
- Prefer reusable components.
- Keep modules independent.
- Separate concerns clearly.
- Maintain readable and maintainable code.
- Use dependency injection where appropriate.
- Write type-safe code.
- Prefer async implementations for I/O operations.

---

# Coding Standards

- Follow PEP 8.
- Use snake_case for files and variables.
- Use descriptive function and class names.
- Avoid duplicated code.
- Write meaningful commit messages.
- Keep functions focused on a single responsibility.
- Add type hints wherever possible.
- Maintain consistent formatting across modules.

---

# Testing Strategy

Testing is an essential part of backend development.

Current testing includes:

- Async database fixtures
- Repository testing
- API key encryption tests
- Audit log repository tests
- Notification repository tests

Future testing goals:

- Service layer tests
- API integration tests
- Authentication tests
- End-to-end testing
- Performance testing

---

# Future Scalability

The Modular Monolith architecture allows future migration to microservices.

Potential future services include:

- AI Service
- Analytics Service
- Notification Service
- Billing Service
- Scheduler Service

Each service can be extracted independently without major architectural changes.

---

# Current Implementation Status

## ✅ Completed

- FastAPI backend initialization
- Project structure
- Async SQLAlchemy setup
- Async database session management
- Repository Pattern implementation
- Core models
- Repository implementations
- Initial test suite
- Multi-tenant foundation

---

## 🚧 In Progress

- Supabase Authentication
- RBAC
- Organization Management
- Campaign Scheduler
- Service layer implementation
- API dependency integration

---

## 📋 Planned

- AI integrations
- Analytics
- CRM
- Billing
- Social Media integrations
- Notification service enhancements
- Background workers
- Redis caching
- Docker deployment

---

# Development Roadmap

## Phase 1 — Foundation ✅

- Backend initialization
- Project structure
- Configuration management
- Async database setup
- Repository layer
- Initial models
- Testing foundation

---

## Phase 2 — Core Platform 🚧

- Authentication
- Organizations
- User Management
- RBAC
- API dependencies

---

## Phase 3 — Marketing Features

- Campaign Management
- Campaign Scheduler
- Social Media integrations
- AI integrations

---

## Phase 4 — Business Features

- Analytics
- CRM
- Billing
- Notifications
- Admin

---

# Architecture Notes

The architecture document should be updated whenever significant structural changes are introduced, including:

- New modules
- Layer changes
- Repository changes
- Database architecture updates
- Authentication architecture
- Multi-tenancy changes
- Service architecture changes

This ensures the documentation always reflects the actual implementation.

---

# Document Information

**Version:** 1.1

**Status:** In Progress

**Last Updated:** July 2026

This document represents the current backend architecture and will continue to evolve alongside the project.