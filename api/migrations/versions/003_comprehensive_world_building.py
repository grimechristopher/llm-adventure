"""comprehensive world building - add PostGIS, history tables, wizard sessions, and enhanced schema

Revision ID: 003
Revises: 001
Create Date: 2025-12-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add comprehensive world-building features:
    - PostGIS extension and spatial columns
    - History tables for temporal tracking
    - World generation session tracking
    - Enhanced fact schema with myths/legends
    - Additional location metadata
    """

    # ========== ENABLE POSTGIS ==========
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis;')

    # ========== UPDATE WORLDS TABLE ==========
    op.add_column('worlds', sa.Column('generation_stage', sa.String(length=30), server_default='initial', nullable=True))
    op.add_column('worlds', sa.Column('world_metadata', postgresql.JSONB(), server_default='{}', nullable=True))

    # ========== UPDATE LOCATIONS TABLE ==========
    # Add PostGIS coordinates column
    op.execute("""
        ALTER TABLE locations
        ADD COLUMN coordinates geography(POINT, 4326);
    """)

    # Add new metadata columns
    op.add_column('locations', sa.Column('population', sa.Integer(), nullable=True))
    op.add_column('locations', sa.Column('controlled_by_faction', sa.String(length=100), nullable=True))
    op.add_column('locations', sa.Column('parent_location_id', sa.Integer(), nullable=True))
    op.add_column('locations', sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True))
    op.add_column('locations', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))

    # Add foreign key for parent location (hierarchical structure)
    op.create_foreign_key(
        'fk_locations_parent_location',
        'locations', 'locations',
        ['parent_location_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add constraints
    op.create_check_constraint(
        'check_elevation_range',
        'locations',
        'elevation_meters IS NULL OR (elevation_meters >= -500 AND elevation_meters <= 9000)'
    )

    # Add check constraint for coordinate bounds (-40 to +40 for quarter-Earth)
    op.execute("""
        ALTER TABLE locations
        ADD CONSTRAINT check_coordinates_bounds
        CHECK (
            coordinates IS NULL OR (
                ST_X(coordinates::geometry) >= -40 AND ST_X(coordinates::geometry) <= 40 AND
                ST_Y(coordinates::geometry) >= -40 AND ST_Y(coordinates::geometry) <= 40
            )
        );
    """)

    # Add spatial index on coordinates (GiST)
    op.execute('CREATE INDEX idx_locations_coordinates ON locations USING GIST(coordinates);')

    # Add index on parent_location_id
    op.create_index('ix_locations_parent', 'locations', ['parent_location_id'])

    # ========== CREATE LOCATION_HISTORY TABLE ==========
    op.create_table(
        'location_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('elevation_meters', sa.Integer(), nullable=True),
        sa.Column('population', sa.Integer(), nullable=True),
        sa.Column('controlled_by_faction', sa.String(length=100), nullable=True),
        sa.Column('valid_from', sa.BigInteger(), nullable=False),
        sa.Column('valid_to', sa.BigInteger(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('changed_by_event_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add coordinates column to location_history
    op.execute("""
        ALTER TABLE location_history
        ADD COLUMN coordinates geography(POINT, 4326);
    """)

    # Create indexes for temporal queries
    op.create_index('ix_location_history_location', 'location_history', ['location_id'])
    op.create_index('ix_location_history_temporal', 'location_history', ['location_id', 'valid_from', 'valid_to'])
    op.execute('CREATE INDEX idx_location_history_coordinates ON location_history USING GIST(coordinates);')

    # ========== UPDATE FACTS TABLE ==========
    # Add new columns for temporal tracking, myths, and evolution
    op.add_column('facts', sa.Column('when_occurred', sa.BigInteger(), nullable=True))
    op.add_column('facts', sa.Column('why_context', sa.Text(), nullable=True))
    op.add_column('facts', sa.Column('where_location_history_id', sa.Integer(), nullable=True))
    op.add_column('facts', sa.Column('created_by_character_id', sa.Integer(), nullable=True))
    op.add_column('facts', sa.Column('created_by_event_id', sa.Integer(), nullable=True))
    op.add_column('facts', sa.Column('superseded_by_fact_id', sa.Integer(), nullable=True))
    op.add_column('facts', sa.Column('superseded_at', sa.BigInteger(), nullable=True))
    op.add_column('facts', sa.Column('importance_score', sa.Numeric(precision=3, scale=2), server_default='0.5', nullable=True))
    op.add_column('facts', sa.Column('last_referenced', sa.BigInteger(), nullable=True))
    op.add_column('facts', sa.Column('generated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True))

    # Add foreign keys
    op.create_foreign_key(
        'fk_facts_location_history',
        'facts', 'location_history',
        ['where_location_history_id'], ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_facts_superseded_by',
        'facts', 'facts',
        ['superseded_by_fact_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add check constraints for fact categorization
    # TRUE facts: observed, historical, current_state, deduction, measurement
    # FALSE facts: myth, legend, prophecy, conspiracy, religious, cultural, epic_tale
    op.execute("""
        ALTER TABLE facts
        ADD CONSTRAINT check_fact_category_truth_match
        CHECK (
            (canonical_truth = TRUE AND fact_category IN (
                'observed', 'historical', 'current_state', 'deduction', 'measurement'
            )) OR
            (canonical_truth = FALSE AND fact_category IN (
                'myth', 'legend', 'prophecy', 'conspiracy', 'religious', 'cultural', 'epic_tale'
            ))
        );
    """)

    # Add constraint for importance score bounds
    op.create_check_constraint(
        'check_importance_bounds',
        'facts',
        'importance_score BETWEEN 0.0 AND 1.0'
    )

    # Add constraint for supersession timestamp
    op.create_check_constraint(
        'check_supersession_timestamp',
        'facts',
        '(superseded_by_fact_id IS NULL) OR (superseded_at IS NOT NULL)'
    )

    # Create indexes for fact queries
    op.create_index('ix_facts_category', 'facts', ['fact_category'])
    op.create_index('ix_facts_when_occurred', 'facts', ['when_occurred'])
    op.create_index('ix_facts_importance', 'facts', ['importance_score'])
    op.create_index('ix_facts_location_history', 'facts', ['where_location_history_id'])

    # Partial index for TRUE/FALSE fact queries
    op.execute('CREATE INDEX ix_facts_truth_true ON facts(canonical_truth) WHERE canonical_truth = TRUE;')
    op.execute('CREATE INDEX ix_facts_truth_false ON facts(canonical_truth) WHERE canonical_truth = FALSE;')

    # ========== CREATE FACT_HISTORY TABLE ==========
    op.create_table(
        'fact_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fact_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.String(length=2000), nullable=False),
        sa.Column('fact_category', sa.String(length=30), nullable=False),
        sa.Column('canonical_truth', sa.Boolean(), nullable=False),
        sa.Column('what_type', sa.String(length=50), nullable=True),
        sa.Column('when_occurred', sa.BigInteger(), nullable=True),
        sa.Column('why_context', sa.Text(), nullable=True),
        sa.Column('where_location_history_id', sa.Integer(), nullable=True),
        sa.Column('importance_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('valid_from', sa.BigInteger(), nullable=False),
        sa.Column('valid_to', sa.BigInteger(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('changed_by_event_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['fact_id'], ['facts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['where_location_history_id'], ['location_history.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for temporal queries
    op.create_index('ix_fact_history_fact', 'fact_history', ['fact_id'])
    op.create_index('ix_fact_history_temporal', 'fact_history', ['fact_id', 'valid_from', 'valid_to'])

    # ========== CREATE WORLD_GENERATION_SESSIONS TABLE ==========
    op.create_table(
        'world_generation_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('session_stage', sa.String(length=30), server_default='gathering', nullable=True),
        sa.Column('current_question_type', sa.String(length=50), nullable=True),
        sa.Column('conversation_history', postgresql.JSONB(), server_default='[]', nullable=True),
        sa.Column('gathered_data', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.Column('is_complete', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for session queries
    op.create_index('ix_wg_sessions_world', 'world_generation_sessions', ['world_id'])
    op.create_index('ix_wg_sessions_stage', 'world_generation_sessions', ['session_stage'])


def downgrade() -> None:
    """
    Remove comprehensive world-building features
    """

    # Drop world_generation_sessions table
    op.drop_index('ix_wg_sessions_stage', table_name='world_generation_sessions')
    op.drop_index('ix_wg_sessions_world', table_name='world_generation_sessions')
    op.drop_table('world_generation_sessions')

    # Drop fact_history table
    op.drop_index('ix_fact_history_temporal', table_name='fact_history')
    op.drop_index('ix_fact_history_fact', table_name='fact_history')
    op.drop_table('fact_history')

    # Drop fact indexes and constraints
    op.execute('DROP INDEX IF EXISTS ix_facts_truth_false;')
    op.execute('DROP INDEX IF EXISTS ix_facts_truth_true;')
    op.drop_index('ix_facts_location_history', table_name='facts')
    op.drop_index('ix_facts_importance', table_name='facts')
    op.drop_index('ix_facts_when_occurred', table_name='facts')
    op.drop_index('ix_facts_category', table_name='facts')

    op.drop_constraint('check_supersession_timestamp', 'facts')
    op.drop_constraint('check_importance_bounds', 'facts')
    op.execute('ALTER TABLE facts DROP CONSTRAINT IF EXISTS check_fact_category_truth_match;')

    op.drop_constraint('fk_facts_superseded_by', 'facts')
    op.drop_constraint('fk_facts_location_history', 'facts')

    # Drop fact columns
    op.drop_column('facts', 'generated_at')
    op.drop_column('facts', 'last_referenced')
    op.drop_column('facts', 'importance_score')
    op.drop_column('facts', 'superseded_at')
    op.drop_column('facts', 'superseded_by_fact_id')
    op.drop_column('facts', 'created_by_event_id')
    op.drop_column('facts', 'created_by_character_id')
    op.drop_column('facts', 'where_location_history_id')
    op.drop_column('facts', 'why_context')
    op.drop_column('facts', 'when_occurred')

    # Drop location_history table
    op.execute('DROP INDEX IF EXISTS idx_location_history_coordinates;')
    op.drop_index('ix_location_history_temporal', table_name='location_history')
    op.drop_index('ix_location_history_location', table_name='location_history')
    op.drop_table('location_history')

    # Drop location indexes and constraints
    op.drop_index('ix_locations_parent', table_name='locations')
    op.execute('DROP INDEX IF EXISTS idx_locations_coordinates;')
    op.execute('ALTER TABLE locations DROP CONSTRAINT IF EXISTS check_coordinates_bounds;')
    op.drop_constraint('check_elevation_range', 'locations')
    op.drop_constraint('fk_locations_parent_location', 'locations')

    # Drop location columns
    op.drop_column('locations', 'deleted_at')
    op.drop_column('locations', 'updated_at')
    op.drop_column('locations', 'parent_location_id')
    op.drop_column('locations', 'controlled_by_faction')
    op.drop_column('locations', 'population')
    op.execute('ALTER TABLE locations DROP COLUMN IF EXISTS coordinates;')

    # Drop worlds columns
    op.drop_column('worlds', 'world_metadata')
    op.drop_column('worlds', 'generation_stage')

    # Note: We don't drop PostGIS extension as it might be used by other apps
    # op.execute('DROP EXTENSION IF EXISTS postgis;')
