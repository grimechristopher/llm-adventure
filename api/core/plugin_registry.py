# core/plugin_registry.py
from typing import Dict
from langgraph.graph import StateGraph
from core.plugin_base import Plugin
from core.logging import get_logger

logger = get_logger(__name__)

class PluginRegistry:
    """Registry for managing plugins"""

    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin

        Args:
            plugin: Plugin instance to register

        Raises:
            ValueError: If plugin with same name already registered
        """
        if plugin.name in self.plugins:
            raise ValueError(f"Plugin '{plugin.name}' already registered")

        self.plugins[plugin.name] = plugin
        logger.info("plugin_registered", plugin=plugin.name)

    def get(self, name: str) -> Plugin:
        """
        Get a registered plugin

        Args:
            name: Plugin name

        Returns:
            Plugin instance

        Raises:
            KeyError: If plugin not registered
        """
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' not registered")

        return self.plugins[name]

    def list_plugins(self) -> list[str]:
        """List all registered plugin names"""
        return list(self.plugins.keys())

    def get_graph(self, plugin_name: str, graph_name: str) -> StateGraph:
        """
        Get a specific graph from a plugin

        Args:
            plugin_name: Plugin name
            graph_name: Graph name

        Returns:
            StateGraph instance

        Raises:
            KeyError: If plugin or graph not found
        """
        plugin = self.get(plugin_name)

        if graph_name not in plugin.graphs:
            raise KeyError(f"Graph '{graph_name}' not found in plugin '{plugin_name}'")

        return plugin.graphs[graph_name]
