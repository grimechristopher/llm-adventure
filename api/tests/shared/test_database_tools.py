# tests/shared/test_database_tools.py
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from contextlib import asynccontextmanager

@pytest.mark.asyncio
async def test_query_database():
    """Test querying database returns results"""
    from shared.tools.database import query_database

    # Create mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "Test"}]
    mock_cursor.__aenter__.return_value = mock_cursor
    mock_cursor.__aexit__.return_value = None

    # Create mock connection - use Mock for cursor() to return sync
    mock_conn = MagicMock()
    mock_conn.cursor = Mock(return_value=mock_cursor)  # Sync method returning async context manager
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    # Patch get_db_connection as async context manager
    @asynccontextmanager
    async def mock_get_db():
        yield mock_conn

    with patch('shared.tools.database.get_db_connection', side_effect=lambda: mock_get_db()):
        result = await query_database.ainvoke({"query": "SELECT * FROM test"})

        assert "Test" in result
        assert "1" in result

@pytest.mark.asyncio
async def test_insert_data():
    """Test inserting data into database"""
    from shared.tools.database import insert_data

    # Create mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = (1,)  # Return tuple for ID
    mock_cursor.__aenter__.return_value = mock_cursor
    mock_cursor.__aexit__.return_value = None

    # Create mock connection
    mock_conn = MagicMock()
    mock_conn.cursor = Mock(return_value=mock_cursor)
    mock_conn.commit = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    # Patch get_db_connection as async context manager
    @asynccontextmanager
    async def mock_get_db():
        yield mock_conn

    with patch('shared.tools.database.get_db_connection', side_effect=lambda: mock_get_db()):
        result = await insert_data.ainvoke({
            "table": "test",
            "data": {"name": "New Item"}
        })

        assert "successfully" in result.lower() or "inserted" in result.lower()

@pytest.mark.asyncio
async def test_update_data():
    """Test updating data in database"""
    from shared.tools.database import update_data

    # Create mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.rowcount = 1
    mock_cursor.__aenter__.return_value = mock_cursor
    mock_cursor.__aexit__.return_value = None

    # Create mock connection
    mock_conn = MagicMock()
    mock_conn.cursor = Mock(return_value=mock_cursor)
    mock_conn.commit = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    # Patch get_db_connection as async context manager
    @asynccontextmanager
    async def mock_get_db():
        yield mock_conn

    with patch('shared.tools.database.get_db_connection', side_effect=lambda: mock_get_db()):
        result = await update_data.ainvoke({
            "table": "test",
            "data": {"name": "Updated"},
            "where": "id = 1"
        })

        assert "updated" in result.lower() or "1" in result

@pytest.mark.asyncio
async def test_execute_transaction():
    """Test executing multiple queries in a transaction"""
    from shared.tools.database import execute_transaction

    # Create mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.__aenter__.return_value = mock_cursor
    mock_cursor.__aexit__.return_value = None

    # Create mock connection
    mock_conn = MagicMock()
    mock_conn.cursor = Mock(return_value=mock_cursor)
    mock_conn.commit = AsyncMock()
    mock_conn.rollback = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    # Patch get_db_connection as async context manager
    @asynccontextmanager
    async def mock_get_db():
        yield mock_conn

    with patch('shared.tools.database.get_db_connection', side_effect=lambda: mock_get_db()):
        queries = [
            "INSERT INTO test (name) VALUES ('Item 1')",
            "INSERT INTO test (name) VALUES ('Item 2')"
        ]
        result = await execute_transaction.ainvoke({"queries": queries})

        assert "success" in result.lower() or "completed" in result.lower()
        assert "2" in result

@pytest.mark.asyncio
async def test_query_database_error_handling():
    """Test query database handles errors gracefully"""
    from shared.tools.database import query_database

    # Create a context manager that raises an exception
    @asynccontextmanager
    async def mock_get_db_error():
        raise Exception("Database connection failed")
        yield  # Never reached

    with patch('shared.tools.database.get_db_connection', side_effect=lambda: mock_get_db_error()):
        result = await query_database.ainvoke({"query": "SELECT * FROM test"})

        assert "failed" in result.lower() or "error" in result.lower()
