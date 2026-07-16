"""brand_kit

Revision ID: 3c_brand_kit
Revises: 2f_audit_notifications_apikeys
Create Date: 2026-07-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c_brand_kit'
down_revision: Union[str, None] = '2f_audit_notifications_apikeys'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('brand_kits',
    sa.Column('brand_name', sa.String(), nullable=False),
    sa.Column('logo_url', sa.String(), nullable=True),
    sa.Column('primary_color', sa.String(length=7), nullable=True),
    sa.Column('secondary_color', sa.String(length=7), nullable=True),
    sa.Column('accent_color', sa.String(length=7), nullable=True),
    sa.Column('font_family', sa.String(length=100), nullable=True),
    sa.Column('brand_voice', sa.String(), nullable=True),
    sa.Column('tone_of_voice', sa.String(), nullable=True),
    sa.Column('brand_description', sa.Text(), nullable=True),
    sa.Column('website_url', sa.String(), nullable=True),
    sa.Column('industry', sa.String(), nullable=True),
    sa.Column('target_audience', sa.Text(), nullable=True),
    sa.Column('default_language', sa.String(length=10), nullable=True),
    sa.Column('ai_writing_instructions', sa.Text(), nullable=True),
    sa.Column('ai_content_restrictions', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_brand_kits_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_brand_kits_updated_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_brand_kits_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_brand_kits')),
    sa.UniqueConstraint('workspace_id', name='uq_brand_kits_workspace_id')
    )
    op.create_index(op.f('ix_brand_kits_deleted_at'), 'brand_kits', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_brand_kits_id'), 'brand_kits', ['id'], unique=False)
    op.create_index(op.f('ix_brand_kits_workspace_id'), 'brand_kits', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('brand_kits')
