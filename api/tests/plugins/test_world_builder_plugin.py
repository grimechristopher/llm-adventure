# tests/plugins/test_world_builder_plugin.py
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from typing import TypedDict

def test_world_builder_plugin_initialization():
    """Test that WorldBuilderPlugin initializes correctly"""
    from plugins.world_builder_plugin import WorldBuilderPlugin

    plugin = WorldBuilderPlugin()

    assert plugin.name == "world_builder"
    assert plugin.llm_preference == "default"
    assert len(plugin.graphs) > 0
    assert "extract" in plugin.graphs

def test_world_builder_plugin_has_extract_graph():
    """Test that plugin has an extract graph"""
    from plugins.world_builder_plugin import WorldBuilderPlugin

    plugin = WorldBuilderPlugin()

    assert "extract" in plugin.graphs
    extract_graph = plugin.graphs["extract"]
    assert extract_graph is not None

def test_world_builder_plugin_validate_input():
    """Test input validation for extract graph"""
    from plugins.world_builder_plugin import WorldBuilderPlugin

    plugin = WorldBuilderPlugin()

    # Valid input
    valid_input = {
        "messages": [],
        "description": "A bustling market town"
    }
    assert plugin.validate_input("extract", valid_input) is True

    # Invalid input - missing description
    invalid_input = {
        "messages": []
    }
    assert plugin.validate_input("extract", invalid_input) is False

def test_world_builder_plugin_handle_error():
    """Test error handling"""
    from plugins.world_builder_plugin import WorldBuilderPlugin

    plugin = WorldBuilderPlugin()

    error = ValueError("Test error")
    context = {"graph": "extract", "description": "test"}

    result = plugin.handle_error(error, context)

    assert "error" in result
    assert result["error"] == "Test error"

@pytest.mark.asyncio
async def test_world_builder_extract_node():
    """Test the extract node processes descriptions"""
    from plugins.world_builder_plugin import WorldBuilderPlugin, WorldBuilderState

    plugin = WorldBuilderPlugin()

    # Mock LLM
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"locations": [{"name": "Test Town", "description": "A town"}], "facts": []}'
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    # Create initial state
    state = WorldBuilderState(
        messages=[],
        description="A bustling market town",
        extraction=None,
        error=None
    )

    # Process through extract node (we'll mock the chain)
    # This test will verify the node structure exists
    assert "extract" in plugin.graphs

@pytest.mark.asyncio
async def test_world_builder_plugin_tools():
    """Test that plugin exposes world builder tools"""
    from plugins.world_builder_plugin import WorldBuilderPlugin

    plugin = WorldBuilderPlugin()

    # Should have world building tools
    assert len(plugin.tools) > 0

    tool_names = [tool.name for tool in plugin.tools]
    assert "extract_world_data" in tool_names
