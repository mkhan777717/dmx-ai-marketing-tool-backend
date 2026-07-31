import asyncio
import os
import sys

# Add the root app dir to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.constants.enums import RoleType
from app.db.session import AsyncSessionLocal
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission

RESOURCES = [
    "Workspace",
    "Campaign",
    "Analytics",
    "Billing",
    "AI",
    "Brand Kit",
    "Assets",
    "Content",
    "Notifications",
    "Members",
    "Reports",
    "Settings",
    "Social Accounts",
    "API Keys",
    "Audit Logs",
]

ACTIONS = ["create", "read", "update", "delete", "manage", "publish"]

# For simplicity, Owner gets everything. Others get a subset.
ROLES_SETUP = {
    "Owner": {"description": "Full access to all resources"},
    "Admin": {"description": "Administrative access, except billing management"},
    "Editor": {"description": "Can create and edit content and campaigns"},
    "Viewer": {"description": "Read-only access to most resources"},
    "Client": {"description": "Restricted read-only access to specific reports"},
}


async def seed_rbac():
    async with AsyncSessionLocal() as db:
        print("Starting RBAC seed...")

        # 1. Create Permissions
        print("Creating Permissions...")
        created_permissions = []
        for resource in RESOURCES:
            res_slug = resource.lower().replace(" ", "_")

            for action in ACTIONS:
                name = f"{res_slug}.{action}"
                # Check if exists
                stmt = select(Permission).where(Permission.name == name)
                result = await db.execute(stmt)
                perm = result.scalar_one_or_none()

                if not perm:
                    perm = Permission(
                        name=name,
                        resource=res_slug,
                        action=action,
                        description=f"Can {action} {resource}",
                        is_system=True,
                    )
                    db.add(perm)
                    created_permissions.append(perm)

        await db.flush()

        # Fetch all permissions to map them
        stmt = select(Permission)
        result = await db.execute(stmt)
        all_permissions = result.scalars().all()

        # 2. Create Roles
        print("Creating System Roles...")
        roles = {}
        for role_name, role_data in ROLES_SETUP.items():
            stmt = select(Role).where(Role.name == role_name, Role.is_system == True)
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()

            if not role:
                role = Role(
                    name=role_name,
                    description=role_data["description"],
                    role_type=RoleType.SYSTEM,
                    is_system=True,
                    workspace_id=None,
                )
                db.add(role)
            roles[role_name] = role

        await db.flush()

        # 3. Map Permissions to Roles
        print("Mapping Role Permissions...")
        for role_name, role in roles.items():
            for perm in all_permissions:
                assign = False

                if role_name == "Owner":
                    assign = True  # Owner gets everything
                elif role_name == "Admin":
                    if perm.resource != "billing" or perm.action != "manage":
                        assign = True
                elif role_name == "Editor":
                    if perm.resource in ["campaign", "content", "assets", "brand_kit"]:
                        if perm.action in ["create", "read", "update", "publish"]:
                            assign = True
                    elif perm.action == "read":
                        assign = True
                elif role_name == "Viewer":
                    if perm.action == "read":
                        assign = True
                elif role_name == "Client":
                    if (
                        perm.resource in ["reports", "analytics", "campaign"]
                        and perm.action == "read"
                    ):
                        assign = True

                if assign:
                    # Check if already mapped
                    stmt = select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    )
                    result = await db.execute(stmt)
                    if not result.scalar_one_or_none():
                        rp = RolePermission(role_id=role.id, permission_id=perm.id)
                        db.add(rp)

        await db.commit()
        print("RBAC seed completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_rbac())
