# AI-Powered Digital Marketing Platform Backend

## Overview
Enterprise SaaS Backend built with FastAPI and Clean Architecture.

## Features
- Multi-Tenant Workspaces
- JWT Authentication & RBAC
- Async PostgreSQL
- Redis Integration

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```
2. Start services (PostgreSQL, Redis):
   ```bash
   docker-compose up -d
   ```
3. Run Alembic migrations (after setup):
   ```bash
   poetry run alembic upgrade head
   ```
4. Run server:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```
