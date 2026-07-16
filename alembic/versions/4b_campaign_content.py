"""campaign_content

Revision ID: 4b_campaign_content
Revises: 4a_campaign
Create Date: 2026-07-15 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4b_campaign_content'
down_revision: Union[str, None] = '4a_campaign'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('campaign_content',
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('content_type', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('hashtags', sa.String(), nullable=True),
    sa.Column('cta', sa.String(), nullable=True),
    sa.Column('seo_title', sa.String(), nullable=True),
    sa.Column('seo_description', sa.String(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('parent_version_id', sa.UUID(), nullable=True),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('scheduled_placeholder', sa.String(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name=op.f('fk_campaign_content_campaign_id_campaigns'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_campaign_content_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['parent_version_id'], ['campaign_content.id'], name=op.f('fk_campaign_content_parent_version_id_campaign_content'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_campaign_content_updated_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_campaign_content_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_campaign_content'))
    )
    op.create_index(op.f('ix_campaign_content_campaign_id'), 'campaign_content', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_campaign_content_content_type'), 'campaign_content', ['content_type'], unique=False)
    op.create_index(op.f('ix_campaign_content_deleted_at'), 'campaign_content', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_campaign_content_id'), 'campaign_content', ['id'], unique=False)
    op.create_index(op.f('ix_campaign_content_language'), 'campaign_content', ['language'], unique=False)
    op.create_index(op.f('ix_campaign_content_status'), 'campaign_content', ['status'], unique=False)
    op.create_index(op.f('ix_campaign_content_version'), 'campaign_content', ['version'], unique=False)
    op.create_index(op.f('ix_campaign_content_workspace_id'), 'campaign_content', ['workspace_id'], unique=False)
    
    op.create_table('campaign_content_assets',
    sa.Column('content_id', sa.UUID(), nullable=False),
    sa.Column('asset_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_campaign_content_assets_asset_id_assets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['content_id'], ['campaign_content.id'], name=op.f('fk_campaign_content_assets_content_id_campaign_content'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('content_id', 'asset_id', name=op.f('pk_campaign_content_assets'))
    )


def downgrade() -> None:
    op.drop_table('campaign_content_assets')
    op.drop_table('campaign_content')
