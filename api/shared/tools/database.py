# shared/tools/database.py
from langchain_core.tools import tool
from typing import Dict, List, Any
import psycopg
from contextlib import asynccontextmanager

# Database connection helper
@asynccontextmanager
async def get_db_connection():
    """Get async database connection"""
    from config.settings import settings

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        yield conn

@tool
async def query_database(query: str, params: Dict[str, Any] = None) -> str:
    """
    Execute a SELECT query on the database

    Args:
        query: SQL SELECT query to execute
        params: Optional dictionary of query parameters

    Returns:
        Query results as formatted text
    """
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)

                results = await cursor.fetchall()

                if not results:
                    return "No results found"

                # Format results
                formatted = []
                for row in results:
                    if isinstance(row, dict):
                        formatted.append(str(row))
                    else:
                        formatted.append(str(row))

                return f"Query returned {len(results)} row(s):\n" + "\n".join(formatted)
    except Exception as e:
        return f"Query failed: {str(e)}"

@tool
async def insert_data(table: str, data: Dict[str, Any]) -> str:
    """
    Insert data into a database table

    Args:
        table: Table name
        data: Dictionary of column: value pairs to insert

    Returns:
        Success message with inserted ID if available
    """
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                columns = ", ".join(data.keys())
                placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
                values = tuple(data.values())

                query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"

                await cursor.execute(query, values)
                result = await cursor.fetchone()

                await conn.commit()

                if result:
                    return f"Successfully inserted data into {table}. ID: {result[0] if isinstance(result, tuple) else result.get('id', 'unknown')}"
                return f"Successfully inserted data into {table}"
    except Exception as e:
        return f"Insert failed: {str(e)}"

@tool
async def update_data(table: str, data: Dict[str, Any], where: str, params: Dict[str, Any] = None) -> str:
    """
    Update data in a database table

    Args:
        table: Table name
        data: Dictionary of column: value pairs to update
        where: WHERE clause (without the WHERE keyword)
        params: Optional dictionary of parameters for the WHERE clause

    Returns:
        Success message with number of rows updated
    """
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                set_clause = ", ".join([f"{col} = ${i+1}" for i, col in enumerate(data.keys())])
                values = list(data.values())

                if params:
                    values.extend(params.values())

                query = f"UPDATE {table} SET {set_clause} WHERE {where}"

                await cursor.execute(query, tuple(values))
                rows_updated = cursor.rowcount

                await conn.commit()

                return f"Successfully updated {rows_updated} row(s) in {table}"
    except Exception as e:
        return f"Update failed: {str(e)}"

@tool
async def execute_transaction(queries: List[str]) -> str:
    """
    Execute multiple queries in a single transaction

    Args:
        queries: List of SQL queries to execute

    Returns:
        Success message with number of queries executed
    """
    try:
        async with get_db_connection() as conn:
            try:
                async with conn.cursor() as cursor:
                    for query in queries:
                        await cursor.execute(query)

                    await conn.commit()

                    return f"Transaction completed successfully. Executed {len(queries)} queries"
            except Exception as e:
                await conn.rollback()
                raise
    except Exception as e:
        return f"Transaction failed: {str(e)}"
