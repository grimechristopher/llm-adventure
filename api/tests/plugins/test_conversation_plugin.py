# tests/plugins/test_conversation_plugin.py
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# Test tool
@tool
def test_search(query: str) -> str:
    """Search for information"""
    return f"Results for: {query}"

def test_conversation_plugin_initialization():
    """Test that ConversationPlugin initializes correctly"""
    from plugins.conversation_plugin import ConversationPlugin

    plugin = ConversationPlugin()

    assert plugin.name == "conversation"
    assert plugin.llm_preference == "default"
    # Graphs are empty until initialized with LLM and tools
    assert len(plugin.graphs) == 0

def test_conversation_plugin_has_chat_graph():
    """Test that plugin has a chat graph after initialization"""
    from plugins.conversation_plugin import ConversationPlugin

    plugin = ConversationPlugin()

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    # Initialize with LLM and tools
    plugin.initialize_with_llm_and_tools(mock_llm, [test_search])

    assert "chat" in plugin.graphs
    chat_graph = plugin.graphs["chat"]
    assert chat_graph is not None

def test_conversation_plugin_validate_input():
    """Test input validation for chat graph"""
    from plugins.conversation_plugin import ConversationPlugin

    plugin = ConversationPlugin()

    # Valid input
    valid_input = {
        "messages": [HumanMessage(content="Hello")]
    }
    assert plugin.validate_input("chat", valid_input) is True

    # Invalid input - missing messages
    invalid_input = {}
    assert plugin.validate_input("chat", invalid_input) is False

def test_conversation_plugin_handle_error():
    """Test error handling"""
    from plugins.conversation_plugin import ConversationPlugin

    plugin = ConversationPlugin()

    error = ValueError("Test error")
    context = {"graph": "chat", "message": "test"}

    result = plugin.handle_error(error, context)

    assert "error" in result
    assert result["error"] == "Test error"

@pytest.mark.asyncio
async def test_conversation_state_tracks_messages():
    """Test that conversation state tracks message history"""
    from plugins.conversation_plugin import ConversationState

    state = ConversationState(
        messages=[
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!")
        ]
    )

    assert len(state["messages"]) == 2
    assert state["messages"][0].content == "Hello"
    assert state["messages"][1].content == "Hi there!"

def test_conversation_plugin_tools():
    """Test that plugin exposes conversation tools"""
    from plugins.conversation_plugin import ConversationPlugin

    plugin = ConversationPlugin()

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    # Initialize with LLM and tools
    tools = [test_search]
    plugin.initialize_with_llm_and_tools(mock_llm, tools)

    # Should have the tools we provided
    assert len(plugin.tools) == 1

    tool_names = [tool.name for tool in plugin.tools]
    assert "test_search" in tool_names

@pytest.mark.asyncio
async def test_conversation_plugin_agent_node():
    """Test that agent node processes messages with LLM"""
    from plugins.conversation_plugin import ConversationPlugin, ConversationState

    plugin = ConversationPlugin()

    # Mock LLM
    mock_llm = MagicMock()
    mock_response = AIMessage(content="I'm doing well, thank you!")
    mock_llm.invoke = MagicMock(return_value=mock_response)
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    # Initialize with LLM and tools
    plugin.initialize_with_llm_and_tools(mock_llm, [test_search])

    # Verify graph exists
    assert "chat" in plugin.graphs
    assert plugin.graphs["chat"] is not None

    # Create initial state
    state = ConversationState(
        messages=[HumanMessage(content="Hello, how are you?")]
    )

    # Test the _call_agent method directly
    result = plugin._call_agent(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "I'm doing well, thank you!"

@pytest.mark.asyncio
async def test_conversation_plugin_should_continue():
    """Test conditional routing logic"""
    from plugins.conversation_plugin import ConversationPlugin, ConversationState
    from langchain_core.messages import AIMessage

    plugin = ConversationPlugin()

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    # Initialize with LLM and tools
    plugin.initialize_with_llm_and_tools(mock_llm, [test_search])

    # State with AI response (no tool calls) should END
    state_end = ConversationState(
        messages=[AIMessage(content="Hello!")]
    )

    result_end = plugin._should_continue(state_end)
    assert result_end == "end"

    # State with tool calls should continue to tools
    state_continue = ConversationState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[{"name": "test_search", "args": {"query": "test"}, "id": "call_123"}]
            )
        ]
    )

    result_continue = plugin._should_continue(state_continue)
    assert result_continue == "continue"
