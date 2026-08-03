import uuid
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publish_history import PublishHistory
from app.repositories.base import BaseRepository


class PublishHistoryRepository(BaseRepository[PublishHistory]):
    async def get_by_workspace_id(
        self, db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[PublishHistory]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(self.model.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()


publish_history_repo = PublishHistoryRepository(PublishHistory)
