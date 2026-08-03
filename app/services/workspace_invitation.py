import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import (
    InviteStatus,
    MemberStatus,
    NotificationPriority,
    NotificationType,
)
from app.models.base import get_utc_now
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invite import WorkspaceInvite
from app.operations.audit.service import AuditLogService
from app.repositories.notification import notification_repo
from app.repositories.rbac import role_repo
from app.repositories.user import user_repo
from app.repositories.workspace_invite import workspace_invite_repo
from app.repositories.workspace_member import workspace_member_repo
from app.services.email import email_service


class WorkspaceInvitationService:
    @staticmethod
    async def get_invites(
        db: AsyncSession, workspace_id: uuid.UUID
    ) -> Sequence[WorkspaceInvite]:
        return await workspace_invite_repo.get_pending_invites(db, workspace_id)

    @staticmethod
    async def create_invite(
        db: AsyncSession,
        user: User,
        workspace: Workspace,
        email: str,
        role_id: uuid.UUID,
    ) -> WorkspaceInvite:
        email = email.lower().strip()

        # Only Owner/Admin can invite. Ensure the inviter actually has this right via endpoint RBAC, but we can verify role exists.
        role = await role_repo.get_by_id(db, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        # Prevent duplicate member
        existing_user = await user_repo.get_by_email(db, email)
        if existing_user:
            existing_member = await workspace_member_repo.get_member(
                db, workspace.id, existing_user.id
            )
            if existing_member and existing_member.status != MemberStatus.REMOVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this workspace",
                )

        # Handle pending duplicate invites
        pending = await workspace_invite_repo.get_pending_invites(db, workspace.id)
        for p in pending:
            if p.email == email:
                # Expire the old one so we can create a new one safely.
                # Since we have a partial unique constraint on (workspace, email) WHERE status=PENDING, we MUST revoke/expire the old one first.
                await workspace_invite_repo.revoke_invite(db, p.id)

        expires_at = get_utc_now() + timedelta(days=7)

        invite = await workspace_invite_repo.create_invitation(
            db,
            {
                "workspace_id": workspace.id,
                "email": email,
                "role_id": role_id,
                "inviter_id": user.id,
                "expires_at": expires_at,
            },
        )

        # Send Email via Abstraction
        inviter_name = (
            f"{user.first_name or ''} {user.last_name or ''}".strip() or "A member"
        )
        await email_service.send_invitation(
            email, workspace.name, invite.token, inviter_name
        )

        # Audit
        await AuditLogService.create_audit_log(
            db=db,
            workspace_id=workspace.id,
            actor_id=user.id,
            action="INVITE_SENT",
            resource_type="workspace_invite",
            resource_id=str(invite.id),
            new_values={"email": email, "role_id": str(role_id)},
        )

        # Notice: The notification for invite sent is typically for the inviter or admins. We will notify the inviter for confirmation.
        await notification_repo.create(
            db,
            obj_in={
                "workspace_id": workspace.id,
                "user_id": user.id,
                "title": "Invitation Sent",
                "body": f"Invitation successfully sent to {email}.",
                "type": NotificationType.SYSTEM,
                "priority": NotificationPriority.LOW,
            },
        )

        return invite

    @staticmethod
    async def revoke_invite(
        db: AsyncSession, user: User, workspace: Workspace, invite_id: uuid.UUID
    ) -> WorkspaceInvite:
        invite = await workspace_invite_repo.get_by_id(db, invite_id)
        if not invite or invite.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
            )

        if invite.status != InviteStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending invitations can be revoked",
            )

        invite = await workspace_invite_repo.revoke_invite(db, invite.id)

        # Audit
        await AuditLogService.create_audit_log(
            db=db,
            workspace_id=workspace.id,
            actor_id=user.id,
            action="INVITE_REVOKED",
            resource_type="workspace_invite",
            resource_id=str(invite.id),
        )

        return invite

    @staticmethod
    async def resend_invite(
        db: AsyncSession, user: User, workspace: Workspace, invite_id: uuid.UUID
    ) -> WorkspaceInvite:
        invite = await workspace_invite_repo.get_by_id(db, invite_id)
        if not invite or invite.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
            )

        if invite.status != InviteStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending invitations can be resent",
            )

        # extend expiration
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        invite = await workspace_invite_repo.resend_invite(
            db, invite.id, new_expires_at
        )

        await email_service.resend_invitation(
            invite.email, workspace.name, invite.token
        )

        # Audit
        await AuditLogService.create_audit_log(
            db=db,
            workspace_id=workspace.id,
            actor_id=user.id,
            action="INVITE_RESENT",
            resource_type="workspace_invite",
            resource_id=str(invite.id),
        )

        return invite

    @staticmethod
    async def accept_invite(
        db: AsyncSession, authenticated_user: User, token: str
    ) -> None:
        # Note: we need an authenticated user. According to rules: "preserve the invitation until they authenticate."
        # The frontend forces login/signup. Once authenticated, the user calls POST /invites/{token}/accept.

        invite = await workspace_invite_repo.get_by_token(db, token)
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token"
            )

        if invite.status == InviteStatus.REVOKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has been revoked",
            )

        if invite.status == InviteStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been accepted",
            )

        if invite.status == InviteStatus.EXPIRED or invite.expires_at < get_utc_now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired"
            )

        if invite.email != authenticated_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invitation email does not match authenticated user email",
            )

        # Prevent duplicate member (in case they already got in through other means)
        existing_member = await workspace_member_repo.get_member(
            db, invite.workspace_id, authenticated_user.id
        )
        if existing_member and existing_member.status != MemberStatus.REMOVED:
            # Just accept the invite silently if they are already a member, or raise error.
            pass
        else:
            # Create member
            await workspace_member_repo.create(
                db,
                obj_in={
                    "workspace_id": invite.workspace_id,
                    "user_id": authenticated_user.id,
                    "role_id": invite.role_id,
                    "status": MemberStatus.ACTIVE,
                    "invited_by": invite.inviter_id,
                    "accepted_at": get_utc_now(),
                    "joined_at": get_utc_now(),
                },
            )

        # Accept the invite
        await workspace_invite_repo.accept_invite(db, invite.id)

        # Audit (executed by the user accepting)
        await AuditLogService.create_audit_log(
            db=db,
            workspace_id=invite.workspace_id,
            actor_id=authenticated_user.id,
            action="INVITE_ACCEPTED",
            resource_type="workspace_invite",
            resource_id=str(invite.id),
        )

        # Notify inviter (if they exist)
        if invite.inviter_id:
            await notification_repo.create(
                db,
                obj_in={
                    "workspace_id": invite.workspace_id,
                    "user_id": invite.inviter_id,
                    "title": "Invitation Accepted",
                    "body": f"{authenticated_user.email} has accepted your invitation.",
                    "type": NotificationType.SYSTEM,
                    "priority": NotificationPriority.NORMAL,
                },
            )


workspace_invitation_service = WorkspaceInvitationService()
