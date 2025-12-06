"""
SQLAlchemy database models for LLM Adventure game
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, BigInteger, Numeric, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geography
from datetime import datetime
from db.base import Base


class World(Base):
    """Top-level container for user-created game worlds"""
    __tablename__ = 'worlds'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by_user = Column(String(255))
    generation_stage = Column(String(30), default='initial')
    world_metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    locations = relationship('Location', back_populates='world', cascade='all, delete-orphan')
    facts = relationship('Fact', back_populates='world', cascade='all, delete-orphan')
    generation_sessions = relationship('WorldGenerationSession', back_populates='world', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<World(id={self.id}, name='{self.name}')>"


class Location(Base):
    """Named places within worlds with PostGIS coordinates and relative positioning"""
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location_type = Column(String(50))  # village, city, forest, mountain, etc.

    # Spatial: PostGIS coordinates (WGS84 constrained to -40 to +40 for quarter-Earth)
    coordinates = Column(Geography(geometry_type='POINT', srid=4326))
    elevation_meters = Column(Integer)

    # Keep relative text for context
    relative_position = Column(Text)  # "far north of the capital"

    # Metadata
    population = Column(Integer)
    controlled_by_faction = Column(String(100))
    parent_location_id = Column(Integer, ForeignKey('locations.id', ondelete='SET NULL'))

    # Temporal
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(TIMESTAMP)  # Soft delete

    # Relationships
    world = relationship('World', back_populates='locations')
    facts = relationship('Fact', back_populates='location')
    history = relationship('LocationHistory', back_populates='location', cascade='all, delete-orphan')
    parent = relationship('Location', remote_side=[id], backref='children')

    __table_args__ = (
        CheckConstraint(
            'elevation_meters IS NULL OR (elevation_meters >= -500 AND elevation_meters <= 9000)',
            name='check_elevation_range'
        ),
    )

    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}', world_id={self.world_id})>"


class Fact(Base):
    """Facts about the world - objective statements (TRUE) or cultural narratives (FALSE: myths, legends)"""
    __tablename__ = 'facts'

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)
    content = Column(String(2000), nullable=False)  # The fact statement

    # Categorization
    fact_category = Column(String(30), nullable=False)
    # TRUE: observed, historical, current_state, deduction, measurement
    # FALSE: myth, legend, prophecy, conspiracy, religious, cultural, epic_tale
    canonical_truth = Column(Boolean, default=True)
    what_type = Column(String(50))  # demographic, structural, political, etc.

    # Temporal
    when_occurred = Column(BigInteger)  # In-game time when this happened

    # Narrative
    why_context = Column(Text)  # Additional context

    # Spatial: Reference to historical snapshot (enables temporal queries)
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='SET NULL'))
    where_location_history_id = Column(Integer, ForeignKey('location_history.id', ondelete='SET NULL'))

    # Authorship (for FALSE facts - myths, legends)
    created_by_character_id = Column(Integer)  # NULL for now (character system not built yet)
    created_by_event_id = Column(Integer)

    # Evolution & cleanup
    superseded_by_fact_id = Column(Integer, ForeignKey('facts.id', ondelete='SET NULL'))
    superseded_at = Column(BigInteger)
    importance_score = Column(Numeric(3, 2), default=0.5)  # 0.0 to 1.0
    last_referenced = Column(BigInteger)

    # Meta
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    generated_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    world = relationship('World', back_populates='facts')
    location = relationship('Location', back_populates='facts', foreign_keys=[location_id])
    location_history = relationship('LocationHistory', foreign_keys=[where_location_history_id])
    history = relationship('FactHistory', back_populates='fact', cascade='all, delete-orphan')
    superseded_by = relationship('Fact', remote_side=[id], foreign_keys=[superseded_by_fact_id])

    __table_args__ = (
        CheckConstraint(
            'importance_score BETWEEN 0.0 AND 1.0',
            name='check_importance_bounds'
        ),
        CheckConstraint(
            '(superseded_by_fact_id IS NULL) OR (superseded_at IS NOT NULL)',
            name='check_supersession_timestamp'
        ),
    )

    def __repr__(self):
        return f"<Fact(id={self.id}, category='{self.fact_category}', truth={self.canonical_truth}, content='{self.content[:50]}...')>"


class LocationHistory(Base):
    """Immutable temporal snapshots of location state"""
    __tablename__ = 'location_history'

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='CASCADE'), nullable=False)

    # Snapshot of all mutable fields
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location_type = Column(String(50))
    coordinates = Column(Geography(geometry_type='POINT', srid=4326))
    elevation_meters = Column(Integer)
    population = Column(Integer)
    controlled_by_faction = Column(String(100))

    # Temporal window
    valid_from = Column(BigInteger, nullable=False)  # In-game time when this state started
    valid_to = Column(BigInteger)  # NULL = current state

    # Change tracking
    change_reason = Column(Text)
    changed_by_event_id = Column(Integer)

    # Meta
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    location = relationship('Location', back_populates='history')

    def __repr__(self):
        return f"<LocationHistory(id={self.id}, location_id={self.location_id}, valid_from={self.valid_from}, valid_to={self.valid_to})>"


class FactHistory(Base):
    """Immutable temporal snapshots of fact state"""
    __tablename__ = 'fact_history'

    id = Column(Integer, primary_key=True)
    fact_id = Column(Integer, ForeignKey('facts.id', ondelete='CASCADE'), nullable=False)

    # Snapshot of all mutable fields
    content = Column(String(2000), nullable=False)
    fact_category = Column(String(30), nullable=False)
    canonical_truth = Column(Boolean, nullable=False)
    what_type = Column(String(50))
    when_occurred = Column(BigInteger)
    why_context = Column(Text)
    where_location_history_id = Column(Integer, ForeignKey('location_history.id', ondelete='SET NULL'))
    importance_score = Column(Numeric(3, 2))

    # Temporal window
    valid_from = Column(BigInteger, nullable=False)
    valid_to = Column(BigInteger)  # NULL = current state

    # Change tracking
    change_reason = Column(Text)
    changed_by_event_id = Column(Integer)

    # Meta
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    fact = relationship('Fact', back_populates='history')

    def __repr__(self):
        return f"<FactHistory(id={self.id}, fact_id={self.fact_id}, valid_from={self.valid_from}, valid_to={self.valid_to})>"


class WorldGenerationSession(Base):
    """Track wizard conversation sessions for world building"""
    __tablename__ = 'world_generation_sessions'

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)

    # Session state
    session_stage = Column(String(30), default='gathering')  # gathering, positioning, finalizing, complete
    current_question_type = Column(String(50))

    # Conversation history (JSONB array of {role, content, timestamp})
    conversation_history = Column(JSONB, default=[])

    # Gathered information (JSONB dict)
    gathered_data = Column(JSONB, default={})

    # Completion
    is_complete = Column(Boolean, default=False)
    completed_at = Column(TIMESTAMP)

    # Meta
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    world = relationship('World', back_populates='generation_sessions')

    def __repr__(self):
        return f"<WorldGenerationSession(id={self.id}, world_id={self.world_id}, stage='{self.session_stage}', complete={self.is_complete})>"
