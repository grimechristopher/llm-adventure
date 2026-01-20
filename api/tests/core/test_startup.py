# tests/core/test_startup.py
import pytest

def test_register_core_tools():
    """Test that core tools are registered"""
    from core.startup import register_core_tools
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    register_core_tools(registry)

    # Verify core tools are registered
    assert len(registry.core_tools) > 0

    # Verify specific tools exist
    tool_names = [tool.name for tool in registry.core_tools]

    # Web tools
    assert "web_search" in tool_names
    assert "http_request" in tool_names
    assert "fetch_url" in tool_names

    # Database tools
    assert "query_database" in tool_names
    assert "insert_data" in tool_names
    assert "update_data" in tool_names
    assert "execute_transaction" in tool_names

    # File tools
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_files" in tool_names
    assert "delete_file" in tool_names

def test_get_tools_includes_core_tools():
    """Test that getting tools for a plugin includes core tools"""
    from core.startup import register_core_tools
    from core.tool_registry import ToolRegistry

    registry = ToolRegistry()
    register_core_tools(registry)

    # Get tools for a hypothetical plugin
    tools = registry.get_tools_for_plugin("test_plugin")

    # Should include core tools
    assert len(tools) >= 11  # At least 11 core tools

    tool_names = [tool.name for tool in tools]
    assert "web_search" in tool_names
    assert "query_database" in tool_names
    assert "read_file" in tool_names
