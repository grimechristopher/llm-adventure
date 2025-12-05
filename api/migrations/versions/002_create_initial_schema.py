"""create initial schema - worlds, locations, facts

Revision ID: 001
Revises:
Create Date: 2025-12-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create worlds, locations, and facts tables"""

    # Create worlds table
    op.create_table(
        'worlds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by_user', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create locations table (coordinates column omitted - PostGIS not installed)
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('relative_position', sa.Text(), nullable=True),
        sa.Column('elevation_meters', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create facts table
    op.create_table(
        'facts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.String(length=2000), nullable=False),
        sa.Column('fact_category', sa.String(length=30), nullable=False),
        sa.Column('canonical_truth', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('what_type', sa.String(length=50), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common queries
    op.create_index('ix_locations_world_id', 'locations', ['world_id'])
    op.create_index('ix_facts_world_id', 'facts', ['world_id'])
    op.create_index('ix_facts_location_id', 'facts', ['location_id'])


def downgrade() -> None:
    """Drop all tables"""
    op.drop_index('ix_facts_location_id', table_name='facts')
    op.drop_index('ix_facts_world_id', table_name='facts')
    op.drop_index('ix_locations_world_id', table_name='locations')
    op.drop_table('facts')
    op.drop_table('locations')
    op.drop_table('worlds')
