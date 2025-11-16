"""
Chat routes with streaming support

This module provides endpoints for chatting with the LLM agent.
Supports both streaming and non-streaming responses.
"""

from quart import Blueprint, jsonify, request, current_app, Response
from pydantic import ValidationError
from models.chat import ChatRequest, ChatResponse
from agents.simple_agent import chat_stream
from utils.logging import get_logger

logger = get_logger(__name__)

chat_routes = Blueprint('chat', __name__, url_prefix='/chat')


@chat_routes.route('/', methods=['POST'])
async def chat_endpoint():
    """
    Chat endpoint with streaming support.

    This endpoint:
    1. Validates the incoming request using Pydantic
    2. Retrieves the appropriate LLM
    3. Streams the response back to the client
    4. Automatically saves conversation history to PostgreSQL

    Request body:
        {
            "message": "User's message",
            "session_id": "optional-session-id"  # defaults to "default"
        }

    Returns:
        Streaming response with LLM output
    """
    try:
        # Get JSON data from request
        data = await request.get_json()

        # Validate request data using Pydantic model
        # This will raise ValidationError if the data is invalid
        chat_request = ChatRequest(**data)

        logger.info("Chat request received",
                    session_id=chat_request.session_id,
                    message_length=len(chat_request.message))

    except ValidationError as e:
        # Return validation errors to the client
        logger.warning("Invalid chat request", errors=str(e))
        return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400

    # Get the LLM instance from the app
    llm = current_app.llms.get('lm_studio')
    if not llm:
        logger.error("LLM not available")
        return jsonify({'error': 'LLM not available'}), 503

    # Define an async generator function that streams the response
    async def generate_stream():
        """
        Generator that yields chunks of the LLM response.

        Each chunk is sent to the client as soon as it's available,
        providing a real-time streaming experience.
        """
        try:
            # Iterate through each chunk from the chat_stream generator
            async for chunk in chat_stream(
                llm,
                chat_request.message,
                chat_request.session_id
            ):
                # Yield each chunk to the client
                # The chunk is a piece of text (could be a word, character, or token)
                yield chunk

        except Exception as e:
            logger.error("Error during streaming", error=e)
            # If an error occurs, send it as part of the stream
            yield f"\n\n[Stream Error: {str(e)}]"

    # Return a Response object that streams the data
    # Content-Type: text/plain means we're sending plain text
    # The client will receive chunks as they're generated
    return Response(generate_stream(), content_type='text/plain')
