# plugins/conversation_plugin.py
"""
Conversation Plugin - LangGraph-based conversational agent

This plugin implements a conversational agent with:
- Message history tracking
- LLM-powered responses
- Tool calling capabilities
- Streaming support
"""

from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from core.plugin_base import Plugin
from core.logging import get_logger
from core.llm_factory import LLMFactory

logger = get_logger(__name__)


# ========== STATE DEFINITION ==========

def add_messages(left: list, right: list) -> list:
    """Add messages to the state, merging lists"""
    return left + right


class ConversationState(TypedDict):
    """State for conversation workflow"""
    messages: Annotated[Sequence[BaseMessage], add_messages]


# ========== PLUGIN IMPLEMENTATION ==========

class ConversationPlugin(Plugin):
    """
    Conversation Plugin

    Provides conversational agent capabilities using LangGraph workflows with:
    - Message history management
    - LLM-powered responses
    - Tool calling and execution
    - Streaming support
    """

    def __init__(self):
        # Set name before calling super().__init__()
        self.name = "conversation"
        self.llm_preference = "default"

        super().__init__()

        # LLM will be injected when graph is used
        self.llm = None
        self.tools = []

        # Initialize graphs (will be created with LLM and tools later)
        self.graphs = {}

        logger.info("conversation_plugin_initialized")

    def initialize_with_llm_and_tools(self, llm, tools: list[BaseTool]):
        """
        Initialize the plugin with an LLM and tools

        This must be called before using the graphs.

        Args:
            llm: Language model instance
            tools: List of tools to make available to the agent
        """
        self.llm = llm
        self.tools = tools

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(tools)

        # Create graphs now that we have LLM and tools
        self.graphs = {
            "chat": self._create_chat_graph()
        }

        logger.info("conversation_plugin_initialized_with_llm",
                   tool_count=len(tools))

    def _create_chat_graph(self) -> StateGraph:
        """
        Create the conversation workflow graph

        Graph flow:
        1. agent: LLM processes messages and decides to respond or use tools
        2. tools: Execute any tool calls from the agent
        3. Loop back to agent with tool results, or END
        """
        workflow = StateGraph(ConversationState)

        # Define nodes
        workflow.add_node("agent", self._call_agent)
        workflow.add_node("tools", ToolNode(self.tools))

        # Define edges
        workflow.set_entry_point("agent")

        # Conditional edge: continue to tools or end
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )

        # After tools, always go back to agent
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _call_agent(self, state: ConversationState) -> ConversationState:
        """
        Call the LLM agent with current messages

        The agent can:
        - Respond directly to the user
        - Call tools to gather information
        - Process tool results and formulate responses
        """
        messages = state["messages"]
        logger.info("agent_called", message_count=len(messages))

        try:
            # Invoke LLM with tools bound
            response = self.llm_with_tools.invoke(messages)

            # Log tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info("agent_calling_tools",
                           tool_count=len(response.tool_calls),
                           tools=[tc["name"] for tc in response.tool_calls])

            return {"messages": [response]}

        except Exception as e:
            logger.error("agent_call_failed", error=str(e))
            # Return error message
            error_msg = AIMessage(content=f"I encountered an error: {str(e)}")
            return {"messages": [error_msg]}

    def _should_continue(self, state: ConversationState) -> Literal["continue", "end"]:
        """
        Determine if we should continue to tools or end

        Returns:
            "continue" if there are tool calls to execute
            "end" if the agent gave a final response
        """
        messages = state["messages"]
        last_message = messages[-1]

        # Check if last message has tool calls
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info("routing_to_tools", tool_count=len(last_message.tool_calls))
            return "continue"

        logger.info("routing_to_end")
        return "end"

    def validate_input(self, graph_name: str, input_data: dict) -> bool:
        """
        Validate input data for a specific graph

        Args:
            graph_name: Name of the graph to validate input for
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        if graph_name == "chat":
            # Require messages field
            if "messages" not in input_data:
                logger.warning("validate_input_failed", reason="missing_messages")
                return False

            if not isinstance(input_data["messages"], list):
                logger.warning("validate_input_failed", reason="invalid_messages_type")
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
