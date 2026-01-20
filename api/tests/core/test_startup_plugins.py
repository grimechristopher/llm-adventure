# tests/core/test_startup_plugins.py
import pytest

def test_register_plugins():
    """Test that plugins are registered"""
    from core.startup import register_plugins
    from core.plugin_registry import PluginRegistry

    registry = PluginRegistry()
    register_plugins(registry)

    # Verify plugins are registered
    assert len(registry.list_plugins()) > 0

    # Verify specific plugin exists
    plugin_names = registry.list_plugins()
    assert "world_builder" in plugin_names

def test_registered_plugin_has_graphs():
    """Test that registered plugin has graphs"""
    from core.startup import register_plugins
    from core.plugin_registry import PluginRegistry

    registry = PluginRegistry()
    register_plugins(registry)

    # Get world_builder plugin
    plugin = registry.get("world_builder")

    assert len(plugin.graphs) > 0
    assert "extract" in plugin.graphs

def test_registered_plugin_has_tools():
    """Test that registered plugin has tools"""
    from core.startup import register_plugins
    from core.plugin_registry import PluginRegistry

    registry = PluginRegistry()
    register_plugins(registry)

    # Get world_builder plugin
    plugin = registry.get("world_builder")

    assert len(plugin.tools) > 0
    tool_names = [tool.name for tool in plugin.tools]
    assert "extract_world_data" in tool_names
