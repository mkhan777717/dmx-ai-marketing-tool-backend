import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.constants.enums import MemberStatus

class WorkspaceMemberBase(BaseModel):
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    status: MemberStatus = MemberStatus.PENDING

class WorkspaceMemberCreate(WorkspaceMemberBase):
    invited_by: uuid.UUID | None = None

class WorkspaceMemberUpdate(BaseModel):
    role_id: uuid.UUID | None = None
    status: MemberStatus | None = None

class WorkspaceMemberUpdateRequest(BaseModel):
    role_id: uuid.UUID

class WorkspaceMemberResponse(WorkspaceMemberBase):
    id: uuid.UUID
    invited_by: uuid.UUID | None = None
    accepted_at: datetime | None = None
    joined_at: datetime | None = None
    last_active: datetime | None = None
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
