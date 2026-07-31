from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    async def get_by_slug(self, db: AsyncSession, slug: str) -> Plan | None:
        stmt = select(self.model).where(self.model.slug == slug)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


plan_repo = PlanRepository(Plan)
