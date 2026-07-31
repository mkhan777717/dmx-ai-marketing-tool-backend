import uuid
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.enums import RoleType
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    pass


class RoleRepository(BaseRepository[Role]):
    async def get_system_roles(self, db: AsyncSession) -> Sequence[Role]:
        stmt = (
            select(self.model)
            .where(self.model.is_system == True)
            .order_by(self.model.name)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_workspace_roles(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> Sequence[Role]:
        stmt = (
            select(self.model)
            .where(
                self.model.workspace_id == workspace_id, self.model.is_system == False
            )
            .order_by(self.model.name)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def clone_system_role_to_workspace(
        self,
        db: AsyncSession,
        system_role_id: uuid.UUID,
        workspace_id: uuid.UUID,
        new_name: str,
    ) -> Role | None:
        # Fetch the system role with its permissions
        stmt = (
            select(self.model)
            .options(selectinload(self.model.role_permissions))
            .where(self.model.id == system_role_id, self.model.is_system == True)
        )
        result = await db.execute(stmt)
        system_role = result.scalar_one_or_none()

        if not system_role:
            return None

        # Create the new custom role
        new_role = Role(
            workspace_id=workspace_id,
            name=new_name,
            description=system_role.description,
            role_type=RoleType.CUSTOM,
            is_system=False,
        )
        db.add(new_role)
        await db.flush()

        # Clone permissions
        new_role_permissions = [
            RolePermission(role_id=new_role.id, permission_id=rp.permission_id)
            for rp in system_role.role_permissions
        ]
        db.add_all(new_role_permissions)
        await db.flush()

        return new_role


class RolePermissionRepository(BaseRepository[RolePermission]):
    async def get_role_permissions(
        self, db: AsyncSession, role_id: uuid.UUID
    ) -> Sequence[Permission]:
        stmt = (
            select(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == role_id)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def assign_permission(
        self, db: AsyncSession, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> RolePermission | None:
        # Check if already assigned
        stmt = select(self.model).where(
            self.model.role_id == role_id, self.model.permission_id == permission_id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            return None  # Already exists

        role_perm = RolePermission(role_id=role_id, permission_id=permission_id)
        db.add(role_perm)
        await db.flush()
        return role_perm

    async def remove_permission(
        self, db: AsyncSession, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        stmt = delete(self.model).where(
            self.model.role_id == role_id, self.model.permission_id == permission_id
        )
        result = await db.execute(stmt)
        return result.rowcount > 0


permission_repo = PermissionRepository(Permission)
role_repo = RoleRepository(Role)
role_permission_repo = RolePermissionRepository(RolePermission)
