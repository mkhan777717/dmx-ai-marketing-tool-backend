"""phase_2b

Revision ID: 2b_user_workspace
Revises: 
Create Date: 2026-07-15 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2b_user_workspace'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create plans table
    op.create_table('plans',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('monthly_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('yearly_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('max_users', sa.Integer(), nullable=False),
    sa.Column('max_workspaces', sa.Integer(), nullable=False),
    sa.Column('max_ai_credits', sa.Integer(), nullable=False),
    sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('max_ai_credits >= 0', name=op.f('ck_plans_max_ai_credits')),
    sa.CheckConstraint('max_users >= 0', name=op.f('ck_plans_max_users')),
    sa.CheckConstraint('max_workspaces >= 0', name=op.f('ck_plans_max_workspaces')),
    sa.CheckConstraint('monthly_price >= 0', name=op.f('ck_plans_monthly_price')),
    sa.CheckConstraint('yearly_price >= 0', name=op.f('ck_plans_yearly_price')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_plans')),
    sa.UniqueConstraint('name', name=op.f('uq_plans_name'))
    )
    op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)
    op.create_index(op.f('ix_plans_slug'), 'plans', ['slug'], unique=True)

    # 2. Create users table
    op.create_table('users',
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('first_name', sa.String(), nullable=True),
    sa.Column('last_name', sa.String(), nullable=True),
    sa.Column('avatar_url', sa.String(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('job_title', sa.String(), nullable=True),
    sa.Column('language', sa.String(), nullable=False),
    sa.Column('default_workspace_id', sa.UUID(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.Column('password_changed_at', sa.DateTime(), nullable=True),
    sa.Column('two_factor_enabled', sa.Boolean(), nullable=False),
    sa.Column('onboarding_completed', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_last_login'), 'users', ['last_login'], unique=False)

    # 3. Create user_preferences table
    op.create_table('user_preferences',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('theme', sa.String(), nullable=False),
    sa.Column('timezone', sa.String(), nullable=False),
    sa.Column('date_format', sa.String(), nullable=False),
    sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ai_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_preferences_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_preferences'))
    )
    op.create_index(op.f('ix_user_preferences_id'), 'user_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)

    # 4. Create workspaces table
    op.create_table('workspaces',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('logo_url', sa.String(), nullable=True),
    sa.Column('timezone', sa.String(), nullable=False),
    sa.Column('industry', sa.String(), nullable=True),
    sa.Column('country', sa.String(), nullable=True),
    sa.Column('default_language', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'SUSPENDED', 'ARCHIVED', 'TRIAL', name='workspacestatus'), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=True),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_workspaces_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_workspaces_owner_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], name=op.f('fk_workspaces_plan_id_plans'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_workspaces_updated_by_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workspaces'))
    )
    op.create_index(op.f('ix_workspaces_country'), 'workspaces', ['country'], unique=False)
    op.create_index(op.f('ix_workspaces_deleted_at'), 'workspaces', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_workspaces_id'), 'workspaces', ['id'], unique=False)
    op.create_index(op.f('ix_workspaces_slug'), 'workspaces', ['slug'], unique=True)
    op.create_index(op.f('ix_workspaces_status'), 'workspaces', ['status'], unique=False)

    # 5. Add default_workspace_id foreign key constraint back to users
    op.create_foreign_key(op.f('fk_users_default_workspace_id_workspaces'), 'users', 'workspaces', ['default_workspace_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint(op.f('fk_users_default_workspace_id_workspaces'), 'users', type_='foreignkey')
    op.drop_table('workspaces')
    op.drop_table('user_preferences')
    op.drop_table('users')
    op.drop_table('plans')
