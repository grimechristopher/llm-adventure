"""
Chat agent using LangChain LCEL with streaming and memory

This module implements a chat agent that:
- Uses LangChain Expression Language (LCEL) for chain composition
- Streams responses token-by-token for better UX
- Stores conversation history in PostgreSQL
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from config.database import get_chat_history
from utils.logging import get_logger

logger = get_logger(__name__)


# Define the prompt template for the chat agent
# This creates a structured prompt with system message and conversation history
CHAT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful AI assistant in an adventure game. "
        "You help guide players through their adventure with creative and engaging responses."
    ),
    # MessagesPlaceholder will be filled with the conversation history from the database
    MessagesPlaceholder(variable_name="chat_history"),
    # The current user input
    ("user", "{input}")
])


def create_chat_chain(llm):
    """
    Create a chat chain using LCEL (LangChain Expression Language).

    The chain flow:
    1. CHAT_PROMPT: Formats the prompt with system message, history, and user input
    2. | llm: Sends the formatted prompt to the language model
    3. | StrOutputParser(): Extracts the text content from the LLM response

    Args:
        llm: The language model to use (ChatOpenAI, AzureChatOpenAI, etc.)

    Returns:
        RunnableWithMessageHistory: A chain that includes conversation memory
    """
    # Create the base chain using the pipe operator (|)
    # Each step passes its output to the next step
    base_chain = (
        CHAT_PROMPT  # Step 1: Build the prompt
        | llm        # Step 2: Send to LLM
        | StrOutputParser()  # Step 3: Parse response to string
    )

    # Wrap the chain with message history capability
    # This automatically loads/saves messages from PostgreSQL
    chain_with_history = RunnableWithMessageHistory(
        base_chain,
        # This function is called to get the history for a given session
        get_session_history=get_chat_history,
        # Tell the chain which input key contains the user's message
        input_messages_key="input",
        # Tell the chain which key to use for storing history
        history_messages_key="chat_history"
    )

    logger.info("Chat chain created with history support")
    return chain_with_history


async def chat_stream(llm, message: str, session_id: str):
    """
    Stream chat responses token-by-token with conversation memory.

    This function:
    1. Creates a chain with the LLM
    2. Streams the response in chunks (tokens)
    3. Automatically saves the conversation to PostgreSQL

    Args:
        llm: The language model instance
        message: The user's input message
        session_id: Unique session identifier for conversation history

    Yields:
        str: Individual chunks (tokens) of the LLM's response as they're generated
    """
    # Create the chain with history
    chain = create_chat_chain(llm)

    # Configuration dict that tells the chain which session to use
    config = {
        "configurable": {
            "session_id": session_id  # This is passed to get_chat_history()
        }
    }

    logger.info("Starting chat stream", session_id=session_id, message_preview=message[:50])

    try:
        # astream() generates response chunks asynchronously
        # Each chunk is a piece of the response (could be a word, character, or token)
        async for chunk in chain.astream(
            {"input": message},  # Input to the chain
            config=config  # Pass the session configuration
        ):
            # Yield each chunk as it arrives
            # The caller can process these chunks immediately (e.g., send to client)
            yield chunk

        logger.info("Chat stream completed successfully", session_id=session_id)

    except Exception as e:
        logger.error("Error during chat stream", error=e, session_id=session_id)
        # Yield error message so the stream doesn't break
        yield f"\n\n[Error: {str(e)}]"