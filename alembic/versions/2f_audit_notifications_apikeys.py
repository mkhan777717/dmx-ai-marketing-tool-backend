"""phase_2f_audit_notifications_apikeys

Revision ID: 2f_audit_notifications_apikeys
Revises: 2e_supabase_auth
Create Date: 2026-07-15 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2f_audit_notifications_apikeys'
down_revision: Union[str, None] = '2e_supabase_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create api_keys table
    op.create_table('api_keys',
    sa.Column('provider', sa.Enum('OPENAI', 'CLAUDE', 'GEMINI', 'META', 'LINKEDIN', 'GOOGLE', 'STRIPE', name='apiprovider'), nullable=False),
    sa.Column('key_name', sa.String(), nullable=False),
    sa.Column('encrypted_secret', sa.String(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_api_keys_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_keys'))
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_is_active'), 'api_keys', ['is_active'], unique=False)
    op.create_index(op.f('ix_api_keys_provider'), 'api_keys', ['provider'], unique=False)
    op.create_index(op.f('ix_api_keys_workspace_id'), 'api_keys', ['workspace_id'], unique=False)

    # 2. Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('resource', sa.String(), nullable=False),
    sa.Column('resource_id', sa.String(), nullable=True),
    sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('metadata_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('request_id', sa.String(), nullable=True),
    sa.Column('ip_address', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_audit_logs_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_request_id'), 'audit_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource'), 'audit_logs', ['resource'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_workspace_id'), 'audit_logs', ['workspace_id'], unique=False)

    # 3. Create notifications table
    op.create_table('notifications',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('body', sa.String(), nullable=False),
    sa.Column('type', sa.Enum('SYSTEM', 'ALERT', 'MESSAGE', 'BILLING', name='notificationtype'), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', 'URGENT', name='notificationpriority'), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_notifications_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_priority'), 'notifications', ['priority'], unique=False)
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_workspace_id'), 'notifications', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
