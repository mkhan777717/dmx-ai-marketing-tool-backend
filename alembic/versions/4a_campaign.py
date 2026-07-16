"""campaign

Revision ID: 4a_campaign
Revises: 3d_asset
Create Date: 2026-07-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a_campaign'
down_revision: Union[str, None] = '3d_asset'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('campaigns',
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('brand_kit_id', sa.UUID(), nullable=True),
    sa.Column('campaign_name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('objective', sa.String(), nullable=True),
    sa.Column('campaign_type', sa.String(), nullable=True),
    sa.Column('target_channels', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('budget', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['brand_kit_id'], ['brand_kits.id'], name=op.f('fk_campaigns_brand_kit_id_brand_kits'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_campaigns_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_campaigns_owner_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_campaigns_updated_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_campaigns_workspace_id_workspaces'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_campaigns'))
    )
    op.create_index(op.f('ix_campaigns_deleted_at'), 'campaigns', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_campaigns_id'), 'campaigns', ['id'], unique=False)
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'], unique=False)
    op.create_index(op.f('ix_campaigns_workspace_id'), 'campaigns', ['workspace_id'], unique=False)
    op.create_index('ix_campaigns_workspace_name', 'campaigns', ['workspace_id', 'campaign_name'], unique=True)
    
    op.create_table('campaign_assets',
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('asset_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_campaign_assets_asset_id_assets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name=op.f('fk_campaign_assets_campaign_id_campaigns'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('campaign_id', 'asset_id', name=op.f('pk_campaign_assets'))
    )


def downgrade() -> None:
    op.drop_table('campaign_assets')
    op.drop_table('campaigns')
