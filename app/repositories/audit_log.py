import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.audit_log import AuditLog

class AuditLogRepository(BaseRepository[AuditLog]):
    async def get_by_organization(self, db: AsyncSession, organization_id: uuid.UUID, limit: int = 100) -> Sequence[AuditLog]:
        stmt = (
    select(self.model)
    .where(self.model.organization_id == organization_id)
    .order_by(self.model.created_at.desc())
    .limit(limit)
)
        
        result = await db.execute(stmt)
        return result.scalars().all()

audit_log_repo = AuditLogRepository(AuditLog)
