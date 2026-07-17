import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Any

class AuditLogBase(BaseModel):
    workspace_id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    resource: str
    resource_id: str | None = None
    old_values: dict[str, Any] | list[Any] | None = None
    new_values: dict[str, Any] | list[Any] | None = None
    metadata_info: dict[str, Any] | list[Any] | None = None
    request_id: str | None = None
    ip_address: str | None = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
