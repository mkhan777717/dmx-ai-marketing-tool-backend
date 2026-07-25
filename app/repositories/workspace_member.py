import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.repositories.base import BaseRepository
from app.models.workspace_member import WorkspaceMember
from app.constants.enums import MemberStatus
from datetime import datetime, timezone

class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    async def get_by_workspace(self, db: AsyncSession, workspace_id: uuid.UUID) -> Sequence[WorkspaceMember]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> Sequence[WorkspaceMember]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_active_members(self, db: AsyncSession, workspace_id: uuid.UUID) -> Sequence[WorkspaceMember]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.status == MemberStatus.ACTIVE,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_member(self, db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceMember | None:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.user_id == user_id,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def change_role(self, db: AsyncSession, member_id: uuid.UUID, new_role_id: uuid.UUID) -> WorkspaceMember | None:
        member = await self.get_by_id(db, member_id)
        if member:
            member.role_id = new_role_id
            db.add(member)
            await db.flush()
            await db.refresh(member)
        return member

    async def suspend_member(self, db: AsyncSession, member_id: uuid.UUID) -> WorkspaceMember | None:
        member = await self.get_by_id(db, member_id)
        if member:
            member.status = MemberStatus.SUSPENDED
            db.add(member)
            await db.flush()
            await db.refresh(member)
        return member

    async def reactivate_member(self, db: AsyncSession, member_id: uuid.UUID) -> WorkspaceMember | None:
        member = await self.get_by_id(db, member_id)
        if member:
            member.status = MemberStatus.ACTIVE
            db.add(member)
            await db.flush()
            await db.refresh(member)
        return member

    async def remove_member(self, db: AsyncSession, member_id: uuid.UUID) -> WorkspaceMember | None:
        member = await self.get_by_id(db, member_id)
        if member:
            member.status = MemberStatus.REMOVED
            from app.models.base import get_utc_now
            member.deleted_at = get_utc_now()
            db.add(member)
            await db.flush()
            await db.refresh(member)
        return member

    async def transfer_ownership(
        self, db: AsyncSession, workspace_id: uuid.UUID, old_owner_id: uuid.UUID, new_owner_id: uuid.UUID, new_role_id: uuid.UUID
    ) -> bool:
        # Atomic update of workspace owner is handled in the workspace repository. 
        # Here we just demote the old owner to their new role.
        old_owner_member = await self.get_member(db, workspace_id, old_owner_id)
        if old_owner_member:
            old_owner_member.role_id = new_role_id
            db.add(old_owner_member)
            await db.flush()
        return True

    async def count_members(self, db: AsyncSession, workspace_id: uuid.UUID) -> int:
        stmt = select(func.count(self.model.id)).where(
            self.model.workspace_id == workspace_id,
            self.model.status == MemberStatus.ACTIVE,
            self.model.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

workspace_member_repo = WorkspaceMemberRepository(WorkspaceMember)
