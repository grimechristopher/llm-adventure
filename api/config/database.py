"""
PostgreSQL database configuration for LLM Adventure API

This module handles the PostgreSQL connection for storing chat history.
"""

import os
import psycopg
from langchain_postgres import PostgresChatMessageHistory
from utils.logging import get_logger

logger = get_logger(__name__)

# Global connection object (created once on startup)
_db_connection = None


def get_postgres_connection_string():
    """
    Build PostgreSQL connection string from environment variables.

    Returns:
        str: PostgreSQL connection URL in format:
             postgresql://user:password@host:port/database
    """
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DB', 'llm_adventure')

    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    logger.info("PostgreSQL connection string built",
                host=host, port=port, database=database, user=user)

    return connection_string


def test_postgres_connection():
    """
    Test basic PostgreSQL connection without initializing tables.

    Returns:
        bool: True if connection successful, False otherwise
    """
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT')
    database = os.getenv('POSTGRES_DB')

    try:
        logger.info("Testing PostgreSQL connection",
                   host=host, port=port, database=database, user=user)

        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password
        )

        # Test the connection with a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        cursor.close()
        conn.close()

        logger.info("PostgreSQL connection successful", postgres_version=version[0])
        return True

    except Exception as e:
        logger.error("PostgreSQL connection failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    host=host,
                    port=port,
                    database=database)
        return False


def get_db_connection():
    """
    Get or create the database connection.

    Returns:
        psycopg.Connection: Active database connection
    """
    global _db_connection

    if _db_connection is None or _db_connection.closed:
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'llm_adventure')

        _db_connection = psycopg.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password
        )
        logger.info("Database connection created")

    return _db_connection


def get_chat_history(session_id: str) -> PostgresChatMessageHistory:
    """
    Get a chat message history for a specific session.

    This creates a PostgresChatMessageHistory instance that automatically
    stores and retrieves chat messages from PostgreSQL for the given session.

    Args:
        session_id: Unique identifier for the chat session (e.g., user ID or session UUID)

    Returns:
        PostgresChatMessageHistory: History object that manages chat messages for this session
    """
    conn = get_db_connection()

    # Create a PostgresChatMessageHistory instance
    # PostgresChatMessageHistory requires positional args: table_name, session_id
    # and sync_connection as a keyword arg (must be a connection object, not string)
    history = PostgresChatMessageHistory(
        "chat_message_history",  # Table name (positional arg)
        session_id,              # Session ID (positional arg)
        sync_connection=conn     # Connection object (keyword arg)
    )

    logger.info("Chat history retrieved", session_id=session_id)

    return history


async def initialize_database():
    """
    Initialize database tables for chat history.

    This is called on application startup to ensure the database
    and required tables exist.
    """
    try:
        # Get connection
        conn = get_db_connection()

        # Create the table schema
        table_name = "chat_message_history"
        PostgresChatMessageHistory.create_tables(conn, table_name)

        logger.info("Database tables created successfully", table_name=table_name)
        return True
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e), error_type=type(e).__name__)
        return False
