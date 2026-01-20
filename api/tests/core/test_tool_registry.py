# tests/core/test_tool_registry.py
import pytest
from langchain.tools import tool

@tool
def test_core_tool(query: str) -> str:
    """A test core tool"""
    return f"core: {query}"

@tool
def test_plugin_tool(query: str) -> str:
    """A test plugin tool"""
    return f"plugin: {query}"

def test_tool_registry_registers_core_tools():
    """Test registering core tools"""
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_core_tool(test_core_tool)

    assert len(registry.core_tools) == 1
    assert registry.core_tools[0].name == "test_core_tool"

def test_tool_registry_registers_plugin_tools():
    """Test registering plugin-specific tools"""
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_plugin_tool("test_plugin", test_plugin_tool)

    assert "test_plugin" in registry.plugin_tools
    assert len(registry.plugin_tools["test_plugin"]) == 1

def test_get_tools_for_plugin_returns_core_and_plugin_tools():
    """Test getting tools for a specific plugin includes core + plugin tools"""
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_core_tool(test_core_tool)
    registry.register_plugin_tool("test_plugin", test_plugin_tool)

    tools = registry.get_tools_for_plugin("test_plugin")

    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "test_core_tool" in tool_names
    assert "test_plugin_tool" in tool_names
