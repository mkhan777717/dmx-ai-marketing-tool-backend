import uuid
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.constants.enums import WorkspaceStatus

class WorkspaceBase(BaseModel):
    name: str
    slug: str
    logo_url: str | None = None
    timezone: str = "UTC"
    industry: str | None = None
    country: str | None = None
    default_language: str = "en"
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    plan_id: uuid.UUID | None = None

class WorkspaceCreate(WorkspaceBase):
    slug: str | None = None

class WorkspaceCreateInternal(WorkspaceCreate):
    owner_id: uuid.UUID
    created_by: uuid.UUID

class WorkspaceTransferOwnershipRequest(BaseModel):
    new_owner_id: uuid.UUID
    new_role_id: uuid.UUID  # The role the old owner will take

class WorkspaceUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    logo_url: str | None = None
    timezone: str | None = None
    industry: str | None = None
    country: str | None = None
    default_language: str | None = None
    status: WorkspaceStatus | None = None
    plan_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
