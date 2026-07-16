from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.workspace import Workspace

class WorkspaceRepository(BaseRepository[Workspace]):
    async def get_by_slug(self, db: AsyncSession, slug: str, include_deleted: bool = False) -> Workspace | None:
        stmt = select(self.model).where(self.model.slug == slug)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

workspace_repo = WorkspaceRepository(Workspace)
