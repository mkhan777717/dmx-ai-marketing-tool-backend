from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.plan import Plan

class PlanRepository(BaseRepository[Plan]):
    async def get_by_slug(self, db: AsyncSession, slug: str) -> Plan | None:
        stmt = select(self.model).where(self.model.slug == slug)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

plan_repo = PlanRepository(Plan)
