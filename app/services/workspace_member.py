import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_member import workspace_member_repo
from app.repositories.rbac import role_repo
from app.repositories.audit_log import audit_log_repo
from app.repositories.notification import notification_repo
from app.constants.enums import MemberStatus, NotificationType, NotificationPriority

class WorkspaceMemberService:
    @staticmethod
    async def get_members(db: AsyncSession, workspace_id: uuid.UUID) -> Sequence[WorkspaceMember]:
        return await workspace_member_repo.get_by_workspace(db, workspace_id)
        
    @staticmethod
    async def get_member(db: AsyncSession, workspace_id: uuid.UUID, member_id: uuid.UUID) -> WorkspaceMember:
        member = await workspace_member_repo.get_by_id(db, member_id)
        if not member or member.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member

    @staticmethod
    async def _protect_owner_role(db: AsyncSession, workspace_id: uuid.UUID, member_to_modify: WorkspaceMember) -> None:
        """Ensures that the workspace has at least one active owner before removing or demoting an owner."""
        # Find Owner role
        system_roles = await role_repo.get_system_roles(db)
        owner_role = next((r for r in system_roles if r.name == "Owner"), None)
        if not owner_role:
            return
            
        if member_to_modify.role_id == owner_role.id and member_to_modify.status == MemberStatus.ACTIVE:
            # We are modifying an active owner. Check if there are other active owners.
            members = await workspace_member_repo.get_active_members(db, workspace_id)
            active_owners = [m for m in members if m.role_id == owner_role.id]
            if len(active_owners) <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove or demote the last active owner of the workspace.")

    @staticmethod
    async def change_role(db: AsyncSession, user: User, workspace: Workspace, member_id: uuid.UUID, new_role_id: uuid.UUID) -> WorkspaceMember:
        member = await WorkspaceMemberService.get_member(db, workspace.id, member_id)
        
        if member.role_id == new_role_id:
            return member
            
        await WorkspaceMemberService._protect_owner_role(db, workspace.id, member)
        
        # Verify role exists
        role = await role_repo.get_by_id(db, new_role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
            
        # Optional: prevent setting to Owner if only current Owner can transfer ownership. 
        # The requirements say "only Owner can transfer ownership", "change Owner role".
        # We assume the API endpoint uses require_permission("member", "update") and the role constraint is checked here.
        # But for strictly adhering to "only Owner can change Owner role", we will enforce that the actor is the workspace owner if new_role is Owner.
        system_roles = await role_repo.get_system_roles(db)
        owner_role = next((r for r in system_roles if r.name == "Owner"), None)
        
        if (new_role_id == owner_role.id or member.role_id == owner_role.id) and workspace.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace owner can assign or remove the Owner role.")

        old_role_id = member.role_id
        member = await workspace_member_repo.change_role(db, member.id, new_role_id)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPDATE_MEMBER_ROLE",
            "resource": "workspace_member",
            "resource_id": str(member.id),
            "old_values": {"role_id": str(old_role_id)},
            "new_values": {"role_id": str(new_role_id)}
        })
        
        # Notify user
        await notification_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": member.user_id,
            "title": "Role Updated",
            "body": f"Your role in {workspace.name} has been updated to {role.name}.",
            "type": NotificationType.SYSTEM,
            "priority": NotificationPriority.NORMAL
        })
        
        return member

    @staticmethod
    async def suspend_member(db: AsyncSession, user: User, workspace: Workspace, member_id: uuid.UUID) -> WorkspaceMember:
        member = await WorkspaceMemberService.get_member(db, workspace.id, member_id)
        
        if member.status == MemberStatus.SUSPENDED:
            return member
            
        await WorkspaceMemberService._protect_owner_role(db, workspace.id, member)
        
        member = await workspace_member_repo.suspend_member(db, member.id)
        
        # Audit
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "SUSPEND_MEMBER",
            "resource": "workspace_member",
            "resource_id": str(member.id)
        })
        
        # Notify
        await notification_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": member.user_id,
            "title": "Account Suspended",
            "body": f"Your access to {workspace.name} has been suspended.",
            "type": NotificationType.ALERT,
            "priority": NotificationPriority.HIGH
        })
        
        return member

    @staticmethod
    async def reactivate_member(db: AsyncSession, user: User, workspace: Workspace, member_id: uuid.UUID) -> WorkspaceMember:
        member = await WorkspaceMemberService.get_member(db, workspace.id, member_id)
        
        if member.status == MemberStatus.ACTIVE:
            return member
            
        member = await workspace_member_repo.reactivate_member(db, member.id)
        
        # Audit
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "REACTIVATE_MEMBER",
            "resource": "workspace_member",
            "resource_id": str(member.id)
        })
        
        # Notify
        await notification_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": member.user_id,
            "title": "Account Reactivated",
            "body": f"Your access to {workspace.name} has been restored.",
            "type": NotificationType.SYSTEM,
            "priority": NotificationPriority.NORMAL
        })
        
        return member

    @staticmethod
    async def remove_member(db: AsyncSession, user: User, workspace: Workspace, member_id: uuid.UUID) -> None:
        member = await WorkspaceMemberService.get_member(db, workspace.id, member_id)
        
        if workspace.owner_id != user.id:
            # Rules: Only Owner can remove members. Wait, is it? "Only Owner can remove members". Yes.
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace owner can remove members.")
            
        await WorkspaceMemberService._protect_owner_role(db, workspace.id, member)
        
        await workspace_member_repo.remove_member(db, member.id)
        
        # Audit
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "REMOVE_MEMBER",
            "resource": "workspace_member",
            "resource_id": str(member.id)
        })
        
        # Notify
        await notification_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": member.user_id,
            "title": "Removed from Workspace",
            "body": f"You have been removed from {workspace.name}.",
            "type": NotificationType.ALERT,
            "priority": NotificationPriority.HIGH
        })

workspace_member_service = WorkspaceMemberService()
