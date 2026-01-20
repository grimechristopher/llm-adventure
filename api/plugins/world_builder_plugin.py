# plugins/world_builder_plugin.py
"""
World Builder Plugin - LangGraph-based world building workflow

This plugin wraps the world building functionality into a LangGraph state machine
for structured data extraction from natural language descriptions.
"""

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage

from core.plugin_base import Plugin
from core.logging import get_logger

logger = get_logger(__name__)


# ========== STATE DEFINITION ==========

class WorldBuilderState(TypedDict):
    """State for world building workflow"""
    messages: List[BaseMessage]
    description: str
    extraction: Optional[Dict[str, Any]]
    error: Optional[str]


# ========== PLUGIN IMPLEMENTATION ==========

class WorldBuilderPlugin(Plugin):
    """
    World Builder Plugin

    Provides structured data extraction from natural language world descriptions
    using LangGraph workflows.
    """

    def __init__(self):
        # Set name before calling super().__init__() since Plugin base class uses it
        self.name = "world_builder"
        self.llm_preference = "default"

        super().__init__()

        # Initialize graphs
        self.graphs = {
            "extract": self._create_extract_graph()
        }

        # Initialize tools
        self.tools = [
            extract_world_data
        ]

        logger.info("world_builder_plugin_initialized", graphs=list(self.graphs.keys()))

    def _create_extract_graph(self) -> StateGraph:
        """
        Create the extraction workflow graph

        Graph flow:
        1. extract_node: Extract locations and facts from description
        2. validate_node: Validate the extraction
        3. END or error_node
        """
        workflow = StateGraph(WorldBuilderState)

        # Define nodes
        workflow.add_node("extract", self._extract_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("error", self._error_node)

        # Define edges
        workflow.set_entry_point("extract")
        workflow.add_conditional_edges(
            "extract",
            self._route_after_extract,
            {
                "validate": "validate",
                "error": "error"
            }
        )
        workflow.add_edge("validate", END)
        workflow.add_edge("error", END)

        return workflow.compile()

    def _extract_node(self, state: WorldBuilderState) -> WorldBuilderState:
        """
        Extract structured data from description

        Uses the world builder chain to parse natural language into
        locations and facts.
        """
        logger.info("extract_node_started", description_length=len(state["description"]))

        try:
            # For now, return a simple extraction
            # In a full implementation, this would use the world_builder chain
            extraction = {
                "locations": [],
                "facts": []
            }

            # Simple parsing logic (placeholder for actual LLM extraction)
            if "town" in state["description"].lower():
                extraction["locations"].append({
                    "name": "Unknown Town",
                    "description": state["description"],
                    "location_type": "town"
                })

            state["extraction"] = extraction
            logger.info("extract_node_complete",
                       locations_count=len(extraction["locations"]),
                       facts_count=len(extraction["facts"]))

        except Exception as e:
            logger.error("extract_node_failed", error=str(e))
            state["error"] = str(e)

        return state

    def _validate_node(self, state: WorldBuilderState) -> WorldBuilderState:
        """Validate the extracted data"""
        logger.info("validate_node_started")

        extraction = state.get("extraction")
        if not extraction:
            state["error"] = "No extraction data to validate"
            return state

        # Basic validation
        if not extraction.get("locations") and not extraction.get("facts"):
            state["error"] = "Extraction contains no locations or facts"

        logger.info("validate_node_complete")
        return state

    def _error_node(self, state: WorldBuilderState) -> WorldBuilderState:
        """Handle errors in the workflow"""
        logger.error("error_node_reached", error=state.get("error"))
        return state

    def _route_after_extract(self, state: WorldBuilderState) -> str:
        """Route after extraction based on success/failure"""
        if state.get("error"):
            return "error"
        return "validate"

    def validate_input(self, graph_name: str, input_data: dict) -> bool:
        """
        Validate input data for a specific graph

        Args:
            graph_name: Name of the graph to validate input for
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        if graph_name == "extract":
            # Require description field
            if "description" not in input_data:
                logger.warning("validate_input_failed", reason="missing_description")
                return False

            if not isinstance(input_data["description"], str):
                logger.warning("validate_input_failed", reason="invalid_description_type")
                return False

            return True

        return False

    def handle_error(self, error: Exception, context: dict) -> dict:
        """
        Handle errors that occur during graph execution

        Args:
            error: The exception that occurred
            context: Context information about where the error occurred

        Returns:
            Error response dict
        """
        logger.error("plugin_error",
                    error_type=type(error).__name__,
                    error_message=str(error),
                    context=context)

        return {
            "error": str(error),
            "error_type": type(error).__name__,
            "context": context
        }


# ========== TOOLS ==========

@tool
async def extract_world_data(description: str) -> dict:
    """
    Extract structured world building data from natural language description

    Args:
        description: Natural language description of world elements

    Returns:
        Dictionary with extracted locations and facts
    """
    logger.info("extract_world_data_tool_called", description_length=len(description))

    try:
        # Simple extraction (placeholder for actual implementation)
        result = {
            "locations": [],
            "facts": [],
            "description": description
        }

        # Basic parsing
        if "town" in description.lower() or "city" in description.lower():
            result["locations"].append({
                "name": "Extracted Location",
                "description": description,
                "location_type": "settlement"
            })

        return result
    except Exception as e:
        logger.error("extract_world_data_failed", error=str(e))
        return {"error": str(e)}
