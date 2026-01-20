# core/startup.py
"""Startup initialization for core components"""

from core.tool_registry import ToolRegistry
from core.plugin_registry import PluginRegistry
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


def register_plugins(registry: PluginRegistry, llm=None, tools=None) -> None:
    """
    Register all plugins in the plugin registry

    Args:
        registry: PluginRegistry instance to register plugins in
        llm: Optional LLM instance for plugins that need it
        tools: Optional list of tools for plugins that need them
    """
    logger.info("registering_plugins")

    # Import plugins
    from plugins.world_builder_plugin import WorldBuilderPlugin
    from plugins.conversation_plugin import ConversationPlugin

    # Register world builder plugin
    world_builder = WorldBuilderPlugin()
    registry.register(world_builder)
    logger.info("registered_plugin",
               name=world_builder.name,
               graphs=len(world_builder.graphs),
               tools=len(world_builder.tools))

    # Register conversation plugin
    conversation = ConversationPlugin()

    # Initialize with LLM and tools if provided
    if llm is not None and tools is not None:
        conversation.initialize_with_llm_and_tools(llm, tools)
        logger.info("conversation_plugin_initialized_with_llm_and_tools")

    registry.register(conversation)
    logger.info("registered_plugin",
               name=conversation.name,
               graphs=len(conversation.graphs),
               tools=len(conversation.tools))

    logger.info("plugins_registered", total=2)
