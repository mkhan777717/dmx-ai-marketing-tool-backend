"""phase_2c_rbac

Revision ID: 2c_rbac
Revises: 2b_user_workspace
Create Date: 2026-07-15 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c_rbac'
down_revision: Union[str, None] = '2b_user_workspace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create permissions table
    op.create_table('permissions',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('resource', sa.String(), nullable=False),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
    sa.UniqueConstraint('resource', 'action', name=op.f('uq_permissions_resource_action'))
    )
    op.create_index(op.f('ix_permissions_action'), 'permissions', ['action'], unique=False)
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'], unique=False)
    op.create_index(op.f('ix_permissions_name'), 'permissions', ['name'], unique=True)
    op.create_index(op.f('ix_permissions_resource'), 'permissions', ['resource'], unique=False)

    # 2. Create roles table
    op.create_table('roles',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('role_type', sa.Enum('SYSTEM', 'CUSTOM', name='roletype'), nullable=False),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_roles_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles'))
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=False)
    op.create_index(op.f('ix_roles_role_type'), 'roles', ['role_type'], unique=False)
    op.create_index(op.f('ix_roles_workspace_id'), 'roles', ['workspace_id'], unique=False)

    # 3. Create role_permissions table
    op.create_table('role_permissions',
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('permission_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], name=op.f('fk_role_permissions_permission_id_permissions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_role_permissions_role_id_roles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_role_permissions')),
    sa.UniqueConstraint('role_id', 'permission_id', name=op.f('uq_role_permissions_role_id_permission_id'))
    )
    op.create_index(op.f('ix_role_permissions_id'), 'role_permissions', ['id'], unique=False)
    op.create_index(op.f('ix_role_permissions_permission_id'), 'role_permissions', ['permission_id'], unique=False)
    op.create_index(op.f('ix_role_permissions_role_id'), 'role_permissions', ['role_id'], unique=False)


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    # RoleType enum is managed automatically by SQLAlchemy ENUM creation, 
    # but could be dropped explicitly if strictly required.
