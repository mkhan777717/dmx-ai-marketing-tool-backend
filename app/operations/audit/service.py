import uuid
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.operations.audit.models import AuditLog
from app.operations.audit.repository import audit_log_repo


class AuditLogService:
    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str,
        workspace_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        metadata_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        obj_in = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "metadata_info": metadata_info,
        }
        return await audit_log_repo.create(db, obj_in=obj_in)

    @staticmethod
    async def get_workspace_audit_logs(
        db: AsyncSession, workspace_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[AuditLog]:
        return await audit_log_repo.get_by_workspace(db, workspace_id, limit, offset)
