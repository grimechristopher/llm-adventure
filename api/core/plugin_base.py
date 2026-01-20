# core/plugin_base.py
from abc import ABC, abstractmethod
from typing import Dict, List
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from core.logging import get_logger

class Plugin(ABC):
    """Base class for all plugins"""

    name: str
    graphs: Dict[str, StateGraph]
    tools: List[BaseTool]
    llm_preference: str

    def __init__(self):
        self.logger = get_logger(f"plugin.{self.name}")

    @abstractmethod
    def validate_input(self, graph_name: str, input_data: dict) -> bool:
        """
        Validate input for a specific graph

        Args:
            graph_name: Name of the graph
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def handle_error(self, error: Exception, context: dict) -> dict:
        """
        Handle plugin-specific errors

        Args:
            error: The exception that occurred
            context: Additional context about the error

        Returns:
            Error response dict
        """
        pass
