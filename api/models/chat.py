"""
Pydantic models for chat API

These models validate and structure request/response data.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.

    Validates incoming chat requests to ensure they have required fields.
    """
    message: str = Field(
        ...,  # Required field
        min_length=1,  # Must have at least 1 character
        max_length=5000,  # Limit message size
        description="The user's message to send to the LLM"
    )

    session_id: Optional[str] = Field(
        default="default",  # Default session if not provided
        description="Session ID to maintain conversation history"
    )


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.

    Structures the response data consistently.
    """
    response: str = Field(
        ...,
        description="The LLM's response to the user's message"
    )

    session_id: str = Field(
        ...,
        description="Session ID for this conversation"
    )
