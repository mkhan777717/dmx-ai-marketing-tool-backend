import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RolePermissionBase(BaseModel):
    role_id: uuid.UUID
    permission_id: uuid.UUID

class RolePermissionCreate(RolePermissionBase):
    pass

class RolePermissionResponse(RolePermissionBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
