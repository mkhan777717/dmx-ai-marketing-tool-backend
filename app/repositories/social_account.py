import uuid
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_account import SocialAccount
from app.repositories.base import BaseRepository


class SocialAccountRepository(BaseRepository[SocialAccount]):
    async def get_by_workspace_id(
        self, db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[SocialAccount]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(self.model.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()


social_account_repo = SocialAccountRepository(SocialAccount)
