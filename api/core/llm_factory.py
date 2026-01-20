# core/llm_factory.py
from typing import Callable, Dict
from langchain_core.language_models import BaseChatModel
from core.logging import get_logger
from config.llm_config import PLUGIN_LLM_PREFERENCES

logger = get_logger(__name__)

class LLMFactory:
    """Factory for creating and managing LLM providers"""

    def __init__(self):
        self.providers: Dict[str, Callable] = {}
        self._cache: Dict[str, BaseChatModel] = {}

    def register(self, name: str, factory: Callable) -> None:
        """
        Register an LLM provider factory function

        Args:
            name: Provider name (e.g., "gpt-4", "local-qwen")
            factory: Function that returns a BaseChatModel instance
        """
        self.providers[name] = factory
        logger.info("llm_provider_registered", provider=name)

    def get(self, name: str, **kwargs) -> BaseChatModel:
        """
        Get an LLM instance by name

        Args:
            name: Provider name
            **kwargs: Additional parameters to pass to the factory

        Returns:
            BaseChatModel instance

        Raises:
            KeyError: If provider not registered
        """
        if name not in self.providers:
            raise KeyError(f"LLM provider '{name}' not registered")

        # Check cache
        cache_key = f"{name}:{str(kwargs)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Create new instance
        llm = self.providers[name](**kwargs)
        self._cache[cache_key] = llm

        logger.info("llm_created", provider=name, kwargs=kwargs)
        return llm

    def get_for_plugin(self, plugin_name: str, **kwargs) -> BaseChatModel:
        """
        Get plugin's preferred LLM

        Args:
            plugin_name: Plugin name
            **kwargs: Additional parameters to pass to the factory

        Returns:
            BaseChatModel instance

        Raises:
            KeyError: If plugin has no preference or provider not registered
        """
        if plugin_name not in PLUGIN_LLM_PREFERENCES:
            raise KeyError(f"No LLM preference for plugin '{plugin_name}'")

        provider_name = PLUGIN_LLM_PREFERENCES[plugin_name]
        return self.get(provider_name, **kwargs)

    def list_providers(self) -> list[str]:
        """List all registered provider names"""
        return list(self.providers.keys())
