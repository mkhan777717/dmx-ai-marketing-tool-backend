import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.constants.enums import RoleType
from app.schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    workspace_id: uuid.UUID | None = None
    role_type: RoleType = RoleType.CUSTOM
    is_system: bool = False


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    # System roles cannot be updated generally, or their types changed.


class RoleResponse(RoleBase):
    id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    role_type: RoleType
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleWithPermissionsResponse(RoleResponse):
    permissions: list[PermissionResponse] = []
