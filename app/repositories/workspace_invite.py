import secrets
import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import InviteStatus
from app.models.base import get_utc_now
from app.models.workspace_invite import WorkspaceInvite
from app.repositories.base import BaseRepository


class WorkspaceInviteRepository(BaseRepository[WorkspaceInvite]):
    async def create_invitation(
        self, db: AsyncSession, obj_in: dict
    ) -> WorkspaceInvite:
        obj_in["email"] = obj_in["email"].lower().strip()
        obj_in["token"] = secrets.token_urlsafe(32)

        invite = self.model(**obj_in)
        db.add(invite)
        await db.flush()
        await db.refresh(invite)
        return invite

    async def get_by_token(
        self, db: AsyncSession, token: str
    ) -> WorkspaceInvite | None:
        stmt = select(self.model).where(self.model.token == token)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_invites(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> Sequence[WorkspaceInvite]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.status == InviteStatus.PENDING,
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def accept_invite(
        self, db: AsyncSession, invite_id: uuid.UUID
    ) -> WorkspaceInvite | None:
        invite = await self.get_by_id(db, invite_id)
        if (
            invite
            and invite.status == InviteStatus.PENDING
            and invite.expires_at > get_utc_now()
        ):
            invite.status = InviteStatus.ACCEPTED
            invite.accepted_at = get_utc_now()
            db.add(invite)
            await db.flush()
            await db.refresh(invite)
            return invite
        return None

    async def revoke_invite(
        self, db: AsyncSession, invite_id: uuid.UUID
    ) -> WorkspaceInvite | None:
        invite = await self.get_by_id(db, invite_id)
        if invite and invite.status == InviteStatus.PENDING:
            invite.status = InviteStatus.REVOKED
            invite.revoked_at = get_utc_now()
            db.add(invite)
            await db.flush()
            await db.refresh(invite)
        return invite

    async def expire_invites(self, db: AsyncSession) -> int:
        now = get_utc_now()
        stmt = (
            update(self.model)
            .where(
                self.model.status == InviteStatus.PENDING, self.model.expires_at <= now
            )
            .values(status=InviteStatus.EXPIRED)
        )

        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def resend_invite(
        self, db: AsyncSession, invite_id: uuid.UUID, new_expires_at: datetime
    ) -> WorkspaceInvite | None:
        invite = await self.get_by_id(db, invite_id)
        if invite and invite.status == InviteStatus.PENDING:
            invite.expires_at = new_expires_at
            # Regenerate token for security reasons optionally, but requirement didn't specify.
            db.add(invite)
            await db.flush()
            await db.refresh(invite)
        return invite


workspace_invite_repo = WorkspaceInviteRepository(WorkspaceInvite)
