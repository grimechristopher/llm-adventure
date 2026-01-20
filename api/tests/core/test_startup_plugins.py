# tests/core/test_startup_plugins.py
import pytest
from unittest.mock import MagicMock

def test_register_plugins():
    """Test that plugins are registered"""
    from core.startup import register_plugins
    from core.plugin_registry import PluginRegistry

    registry = PluginRegistry()
    register_plugins(registry)

    # Verify plugins are registered
    assert len(registry.list_plugins()) >= 2

    # Verify specific plugins exist
    plugin_names = registry.list_plugins()
    assert "world_builder" in plugin_names
    assert "conversation" in plugin_names

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

def test_conversation_plugin_with_llm_and_tools():
    """Test that conversation plugin initializes with LLM and tools"""
    from core.startup import register_plugins
    from core.plugin_registry import PluginRegistry
    from langchain_core.tools import tool

    # Create test tool
    @tool
    def test_tool(query: str) -> str:
        """Test tool"""
        return f"Result: {query}"

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    registry = PluginRegistry()
    register_plugins(registry, llm=mock_llm, tools=[test_tool])

    # Get conversation plugin
    plugin = registry.get("conversation")

    # Should have graphs after initialization
    assert len(plugin.graphs) > 0
    assert "chat" in plugin.graphs

    # Should have tools
    assert len(plugin.tools) == 1
    assert plugin.tools[0].name == "test_tool"
