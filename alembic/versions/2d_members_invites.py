"""phase_2d_members_invites

Revision ID: 2d_members_invites
Revises: 2c_rbac
Create Date: 2026-07-15 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2d_members_invites'
down_revision: Union[str, None] = '2c_rbac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create workspace_members table
    op.create_table('workspace_members',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'SUSPENDED', 'REMOVED', name='memberstatus'), nullable=False),
    sa.Column('invited_by', sa.UUID(), nullable=True),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('joined_at', sa.DateTime(), nullable=True),
    sa.Column('last_active', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_workspace_members_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], name=op.f('fk_workspace_members_invited_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_workspace_members_role_id_roles'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_workspace_members_updated_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_workspace_members_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_workspace_members_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workspace_members')),
    sa.UniqueConstraint('workspace_id', 'user_id', name=op.f('uq_workspace_members_workspace_id_user_id'))
    )
    op.create_index(op.f('ix_workspace_members_deleted_at'), 'workspace_members', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_workspace_members_id'), 'workspace_members', ['id'], unique=False)
    op.create_index(op.f('ix_workspace_members_role_id'), 'workspace_members', ['role_id'], unique=False)
    op.create_index(op.f('ix_workspace_members_status'), 'workspace_members', ['status'], unique=False)
    op.create_index(op.f('ix_workspace_members_user_id'), 'workspace_members', ['user_id'], unique=False)
    op.create_index(op.f('ix_workspace_members_workspace_id'), 'workspace_members', ['workspace_id'], unique=False)

    # 2. Create workspace_invites table
    op.create_table('workspace_invites',
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('inviter_id', sa.UUID(), nullable=True),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED', name='invitestatus'), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], name=op.f('fk_workspace_invites_inviter_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_workspace_invites_role_id_roles'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_workspace_invites_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workspace_invites'))
    )
    op.create_index(op.f('ix_workspace_invites_email'), 'workspace_invites', ['email'], unique=False)
    op.create_index(op.f('ix_workspace_invites_expires_at'), 'workspace_invites', ['expires_at'], unique=False)
    op.create_index(op.f('ix_workspace_invites_id'), 'workspace_invites', ['id'], unique=False)
    op.create_index(op.f('ix_workspace_invites_status'), 'workspace_invites', ['status'], unique=False)
    op.create_index(op.f('ix_workspace_invites_token'), 'workspace_invites', ['token'], unique=True)
    op.create_index(op.f('ix_workspace_invites_workspace_id'), 'workspace_invites', ['workspace_id'], unique=False)
    
    # 3. Create partial index for pending invites
    op.create_index('uq_workspace_invites_workspace_id_email_pending', 'workspace_invites', ['workspace_id', 'email'], unique=True, postgresql_where=sa.text("status = 'PENDING'"))


def downgrade() -> None:
    op.drop_index('uq_workspace_invites_workspace_id_email_pending', table_name='workspace_invites', postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_table('workspace_invites')
    op.drop_table('workspace_members')
