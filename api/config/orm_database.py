"""
SQLAlchemy ORM database configuration for structured game data

This module provides SQLAlchemy ORM sessions for managing structured game entities
like Worlds, Locations, and Facts. Also provides database connectivity testing.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from db.base import Base
from utils.logging import get_logger
import os

logger = get_logger(__name__)

# Build database URL from environment variables
DATABASE_URL = (
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'llm_adventure')}"
)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10
)

# Create session factory for ORM operations
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
)


def get_db_session():
    """
    Get SQLAlchemy database session for ORM operations on game data
    
    Used for: Creating worlds, locations, facts via SQLAlchemy models

    Usage:
        db = next(get_db_session())
        try:
            world = World(name="My World")
            db.add(world)
            db.commit()
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_postgres_connection() -> bool:
    """
    Test basic PostgreSQL connection without initializing tables.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'llm_adventure')
        user = os.getenv('POSTGRES_USER', 'postgres')

        logger.info("Testing PostgreSQL connection",
                   host=host, port=port, database=database, user=user)

        # Test the connection with a simple query using SQLAlchemy
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()

        logger.info("PostgreSQL connection successful", postgres_version=version[0])
        return True

    except Exception as e:
        logger.error("PostgreSQL connection failed",
                    error=str(e),
                    error_type=type(e).__name__)
        return False


async def initialize_database() -> bool:
    """
    Initialize database tables for game data.
    
    This creates all SQLAlchemy model tables (Worlds, Locations, Facts, etc.)
    on application startup if they don't exist.
    """
    try:
        # Create all tables defined in the Base metadata
        Base.metadata.create_all(bind=engine)
        
        logger.info("Game data database tables created successfully")
        return True
        
    except Exception as e:
        logger.error("Failed to initialize game database", 
                    error=str(e), error_type=type(e).__name__)
        return False
