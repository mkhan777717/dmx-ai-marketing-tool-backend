import uuid
import re
from datetime import datetime, timezone
from app.models.base import get_utc_now
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.workspace import Workspace
from app.models.user import User
from app.schemas.workspace import WorkspaceCreateInternal, WorkspaceUpdate, WorkspaceTransferOwnershipRequest
from app.repositories.workspace import workspace_repo
from app.repositories.workspace_member import workspace_member_repo
from app.repositories.rbac import role_repo
from app.repositories.audit_log import audit_log_repo
from app.repositories.notification import notification_repo
from app.constants.enums import MemberStatus, NotificationType, NotificationPriority

class WorkspaceService:
    @staticmethod
    def _generate_slug(name: str) -> str:
        # Basic slugification
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    @staticmethod
    async def create_workspace(db: AsyncSession, user: User, data: WorkspaceCreateInternal) -> Workspace:
        # Generate slug if omitted
        if not data.slug:
            data.slug = WorkspaceService._generate_slug(data.name)
            
        # Ensure slug is unique
        existing = await workspace_repo.get_by_slug(db, data.slug, include_deleted=True)
        if existing:
            # Append random string to make it unique for simplicity, or raise error. We'll raise error.
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace slug already exists.")
            
        # Create workspace
        workspace = await workspace_repo.create(db, obj_in=data.model_dump())
        
        # Get Owner role
        system_roles = await role_repo.get_system_roles(db)
        owner_role = next((r for r in system_roles if r.name == "Owner"), None)
        if not owner_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="System Owner role not found")
            
        # Add creator as ACTIVE member with Owner role
        await workspace_member_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "role_id": owner_role.id,
            "status": MemberStatus.ACTIVE,
            "joined_at": get_utc_now()
        })
        
        # Generate Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "CREATE",
            "resource": "workspace",
            "resource_id": str(workspace.id),
            "new_values": {"name": workspace.name, "slug": workspace.slug}
        })
        
        return workspace

    @staticmethod
    async def update_workspace(db: AsyncSession, user: User, workspace: Workspace, data: WorkspaceUpdate) -> Workspace:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return workspace
            
        if "slug" in update_data and update_data["slug"] != workspace.slug:
            existing = await workspace_repo.get_by_slug(db, update_data["slug"], include_deleted=True)
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace slug already exists.")

        old_values = {k: getattr(workspace, k) for k in update_data.keys()}
        
        updated_workspace = await workspace_repo.update(db, db_obj=workspace, obj_in=update_data)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "UPDATE",
            "resource": "workspace",
            "resource_id": str(workspace.id),
            "old_values": old_values,
            "new_values": update_data
        })
        
        return updated_workspace

    @staticmethod
    async def transfer_ownership(db: AsyncSession, user: User, workspace: Workspace, data: WorkspaceTransferOwnershipRequest) -> Workspace:
        if workspace.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can transfer ownership.")
            
        # Verify new owner is a member
        new_owner_member = await workspace_member_repo.get_member(db, workspace.id, data.new_owner_id)
        if not new_owner_member or new_owner_member.status != MemberStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New owner must be an active member.")
            
        # Get Owner role
        system_roles = await role_repo.get_system_roles(db)
        owner_role = next((r for r in system_roles if r.name == "Owner"), None)
        if not owner_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="System Owner role not found")

        # Execute transfer (Atomic in DB session)
        # 1. Update Workspace owner_id
        await workspace_repo.update(db, db_obj=workspace, obj_in={"owner_id": data.new_owner_id})
        
        # 2. Update new owner's member role to Owner
        await workspace_member_repo.change_role(db, new_owner_member.id, owner_role.id)
        
        # 3. Update old owner's member role
        await workspace_member_repo.transfer_ownership(db, workspace.id, user.id, data.new_owner_id, data.new_role_id)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "TRANSFER_OWNERSHIP",
            "resource": "workspace",
            "resource_id": str(workspace.id),
            "old_values": {"owner_id": str(user.id)},
            "new_values": {"owner_id": str(data.new_owner_id)}
        })
        
        # Notification
        await notification_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": data.new_owner_id,
            "title": "Workspace Ownership Transferred",
            "body": f"You are now the owner of {workspace.name}.",
            "type": NotificationType.SYSTEM,
            "priority": NotificationPriority.HIGH
        })
        
        return workspace

    @staticmethod
    async def delete_workspace(db: AsyncSession, user: User, workspace: Workspace) -> None:
        if workspace.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete the workspace.")
            
        # Soft delete workspace
        await workspace_repo.delete(db, id=workspace.id, soft=True)
        
        # Audit Log
        await audit_log_repo.create(db, obj_in={
            "workspace_id": workspace.id,
            "user_id": user.id,
            "action": "DELETE",
            "resource": "workspace",
            "resource_id": str(workspace.id)
        })

workspace_service = WorkspaceService()
