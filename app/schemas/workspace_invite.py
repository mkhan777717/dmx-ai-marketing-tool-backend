import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.constants.enums import InviteStatus


class WorkspaceInviteBase(BaseModel):
    workspace_id: uuid.UUID
    email: EmailStr
    role_id: uuid.UUID
    status: InviteStatus = InviteStatus.PENDING


class WorkspaceInviteCreate(WorkspaceInviteBase):
    inviter_id: uuid.UUID | None = None


class WorkspaceInviteRequest(BaseModel):
    email: EmailStr
    role_id: uuid.UUID


class WorkspaceInviteUpdate(BaseModel):
    status: InviteStatus | None = None
    role_id: uuid.UUID | None = None


class WorkspaceInviteResponse(WorkspaceInviteBase):
    id: uuid.UUID
    inviter_id: uuid.UUID | None = None
    token: str
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
