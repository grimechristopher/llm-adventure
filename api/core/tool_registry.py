# core/tool_registry.py
from typing import List, Dict
from langchain_core.tools import BaseTool
from core.logging import get_logger

logger = get_logger(__name__)

class ToolRegistry:
    """Registry for managing core and plugin-specific tools"""

    def __init__(self):
        self.core_tools: List[BaseTool] = []
        self.plugin_tools: Dict[str, List[BaseTool]] = {}

    def register_core_tool(self, tool: BaseTool) -> None:
        """
        Register a core tool available to all plugins

        Args:
            tool: The tool to register
        """
        self.core_tools.append(tool)
        logger.info("core_tool_registered", tool_name=tool.name)

    def register_plugin_tool(self, plugin_name: str, tool: BaseTool) -> None:
        """
        Register a plugin-specific tool

        Args:
            plugin_name: Name of the plugin
            tool: The tool to register
        """
        if plugin_name not in self.plugin_tools:
            self.plugin_tools[plugin_name] = []

        self.plugin_tools[plugin_name].append(tool)
        logger.info("plugin_tool_registered", plugin=plugin_name, tool_name=tool.name)

    def get_tools_for_plugin(self, plugin_name: str) -> List[BaseTool]:
        """
        Get all tools available to a plugin (core + plugin-specific)

        Args:
            plugin_name: Name of the plugin

        Returns:
            List of tools available to the plugin
        """
        plugin_specific = self.plugin_tools.get(plugin_name, [])
        return self.core_tools + plugin_specific

    def list_core_tools(self) -> List[str]:
        """List names of all core tools"""
        return [tool.name for tool in self.core_tools]

    def list_plugin_tools(self, plugin_name: str) -> List[str]:
        """List names of all tools for a specific plugin"""
        return [tool.name for tool in self.plugin_tools.get(plugin_name, [])]
