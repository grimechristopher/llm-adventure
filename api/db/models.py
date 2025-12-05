"""
SQLAlchemy database models for LLM Adventure game
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


class World(Base):
    """Top-level container for user-created game worlds"""
    __tablename__ = 'worlds'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by_user = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    locations = relationship('Location', back_populates='world', cascade='all, delete-orphan')
    facts = relationship('Fact', back_populates='world', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<World(id={self.id}, name='{self.name}')>"


class Location(Base):
    """Named places within worlds with relative positioning (PostGIS coordinates omitted - not installed)"""
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location_type = Column(String(50))  # village, city, forest, mountain, etc.
    relative_position = Column(Text)  # "north of Millbrook, 2 days travel by road"
    elevation_meters = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    world = relationship('World', back_populates='locations')
    facts = relationship('Fact', back_populates='location')

    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}', world_id={self.world_id})>"


class Fact(Base):
    """Facts about the world - objective statements that may be true or false"""
    __tablename__ = 'facts'

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)
    content = Column(String(2000), nullable=False)  # The fact statement
    fact_category = Column(String(30), nullable=False)  # observed, historical, current_state, deduction, measurement
    canonical_truth = Column(Boolean, default=True)  # TRUE facts only in v1 (defer myths/legends)
    what_type = Column(String(50))  # demographic, structural, political, social, geographic, etc.
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='SET NULL'))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    world = relationship('World', back_populates='facts')
    location = relationship('Location', back_populates='facts')

    def __repr__(self):
        return f"<Fact(id={self.id}, category='{self.fact_category}', content='{self.content[:50]}...')>"
