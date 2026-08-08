import uuid
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    async def get_by_slug(
        self, db: AsyncSession, slug: str, include_deleted: bool = False
    ) -> Workspace | None:
        stmt = select(self.model).where(self.model.slug == slug)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_workspaces(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Sequence[Workspace]:
        stmt = (
            select(self.model)
            .outerjoin(WorkspaceMember, self.model.id == WorkspaceMember.workspace_id)
            .where(
                or_(self.model.owner_id == user_id, WorkspaceMember.user_id == user_id)
            )
            .where(self.model.deleted_at.is_(None))
            .distinct()
        )
        result = await db.execute(stmt)
        return result.scalars().all()


workspace_repo = WorkspaceRepository(Workspace)
