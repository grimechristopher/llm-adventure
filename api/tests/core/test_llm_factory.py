# tests/core/test_llm_factory.py
import pytest
from unittest.mock import Mock

def test_llm_factory_registers_provider():
    """Test registering an LLM provider"""
    from core.llm_factory import LLMFactory

    factory = LLMFactory()
    mock_llm = Mock()

    def create_mock_llm(**kwargs):
        return mock_llm

    factory.register("mock_llm", create_mock_llm)

    assert "mock_llm" in factory.providers

def test_llm_factory_gets_provider():
    """Test getting an LLM instance"""
    from core.llm_factory import LLMFactory

    factory = LLMFactory()
    mock_llm = Mock()

    def create_mock_llm(**kwargs):
        return mock_llm

    factory.register("mock_llm", create_mock_llm)
    llm = factory.get("mock_llm")

    assert llm == mock_llm

def test_llm_factory_gets_for_plugin():
    """Test getting plugin's preferred LLM"""
    from core.llm_factory import LLMFactory
    from config.llm_config import PLUGIN_LLM_PREFERENCES

    factory = LLMFactory()
    mock_llm = Mock()

    def create_mock_llm(**kwargs):
        return mock_llm

    # Register mock provider
    factory.register("mock_llm", create_mock_llm)

    # Set preference
    PLUGIN_LLM_PREFERENCES["test_plugin"] = "mock_llm"

    llm = factory.get_for_plugin("test_plugin")
    assert llm == mock_llm
