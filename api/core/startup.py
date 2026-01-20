# core/startup.py
"""Startup initialization for core components"""

from core.tool_registry import ToolRegistry
from core.logging import get_logger

logger = get_logger(__name__)

def register_core_tools(registry: ToolRegistry) -> None:
    """
    Register all core tools in the tool registry

    Args:
        registry: ToolRegistry instance to register tools in
    """
    logger.info("registering_core_tools")

    # Import tools
    from shared.tools.web import web_search, http_request, fetch_url
    from shared.tools.database import query_database, insert_data, update_data, execute_transaction
    from shared.tools.file import read_file, write_file, list_files, delete_file

    # Register web tools
    registry.register_core_tool(web_search)
    registry.register_core_tool(http_request)
    registry.register_core_tool(fetch_url)
    logger.info("registered_web_tools", count=3)

    # Register database tools
    registry.register_core_tool(query_database)
    registry.register_core_tool(insert_data)
    registry.register_core_tool(update_data)
    registry.register_core_tool(execute_transaction)
    logger.info("registered_database_tools", count=4)

    # Register file tools
    registry.register_core_tool(read_file)
    registry.register_core_tool(write_file)
    registry.register_core_tool(list_files)
    registry.register_core_tool(delete_file)
    logger.info("registered_file_tools", count=4)

    logger.info("core_tools_registered", total=11)
