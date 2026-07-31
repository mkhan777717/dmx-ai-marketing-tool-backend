import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.operations.audit.models import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    async def get_by_workspace(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .order_by(self.model.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_resource(
        self, db: AsyncSession, resource_type: str, resource_id: str
    ) -> Sequence[AuditLog]:
        stmt = (
            select(self.model)
            .where(
                self.model.resource_type == resource_type,
                self.model.resource_id == resource_id,
            )
            .order_by(self.model.timestamp.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()


audit_log_repo = AuditLogRepository(AuditLog)
