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
    ) -> Sequence[AuditLog]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all()


audit_log_repo = AuditLogRepository(AuditLog)
