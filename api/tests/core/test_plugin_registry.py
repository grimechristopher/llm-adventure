# tests/core/test_plugin_registry.py
import pytest
from typing import Dict
from langgraph.graph import StateGraph

def test_plugin_registry_registers_plugin():
    """Test registering a plugin"""
    from core.plugin_registry import PluginRegistry
    from core.plugin_base import Plugin

    class TestPlugin(Plugin):
        name = "test_plugin"
        llm_preference = "gpt-4"

        def __init__(self):
            super().__init__()
            self.graphs = {}
            self.tools = []

        def validate_input(self, graph_name: str, input_data: dict) -> bool:
            return True

        def handle_error(self, error: Exception, context: dict) -> dict:
            return {"error": str(error)}

    registry = PluginRegistry()
    plugin = TestPlugin()
    registry.register(plugin)

    assert "test_plugin" in registry.plugins
    assert registry.plugins["test_plugin"] == plugin

def test_plugin_registry_gets_plugin():
    """Test getting a registered plugin"""
    from core.plugin_registry import PluginRegistry
    from core.plugin_base import Plugin

    class TestPlugin(Plugin):
        name = "test_plugin"
        llm_preference = "gpt-4"
        graphs = {}
        tools = []

        def validate_input(self, graph_name: str, input_data: dict) -> bool:
            return True

        def handle_error(self, error: Exception, context: dict) -> dict:
            return {"error": str(error)}

    registry = PluginRegistry()
    plugin = TestPlugin()
    registry.register(plugin)

    retrieved = registry.get("test_plugin")
    assert retrieved == plugin

def test_plugin_registry_raises_on_missing_plugin():
    """Test getting non-existent plugin raises KeyError"""
    from core.plugin_registry import PluginRegistry

    registry = PluginRegistry()

    with pytest.raises(KeyError):
        registry.get("nonexistent")
