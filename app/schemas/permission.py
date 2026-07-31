import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionBase(BaseModel):
    name: str
    resource: str
    action: str
    description: str | None = None
    is_system: bool = True


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    description: str | None = None
    # name, resource, action, and is_system are usually immutable after creation


class PermissionResponse(PermissionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
