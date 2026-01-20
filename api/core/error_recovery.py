# core/error_recovery.py
from typing import Callable, TypedDict, Any
from functools import wraps
import time

# Define custom error types
class ToolError(Exception):
    """Raised when a tool execution fails"""
    pass

class ValidationError(Exception):
    """Raised when input validation fails"""
    pass

class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass

class LLMRefusalError(Exception):
    """Raised when LLM refuses to respond"""
    pass

# Recoverable error types
RECOVERABLE_ERRORS = (ToolError, ValidationError, RateLimitError, LLMRefusalError)

def is_recoverable(error: Exception) -> bool:
    """Check if an error is recoverable"""
    return isinstance(error, RECOVERABLE_ERRORS)

def create_retry_node(max_attempts: int = 3, backoff: str = "exponential") -> Callable:
    """
    Create a retry node for LangGraph graphs

    Args:
        max_attempts: Maximum number of retry attempts
        backoff: Backoff strategy ('exponential' or 'linear')

    Returns:
        A node function that increments attempts and applies backoff
    """
    def retry_node(state: dict) -> dict:
        """Retry node that increments attempts"""
        attempts = state.get("attempts", 0) + 1

        # Apply backoff
        if backoff == "exponential":
            delay = 2 ** attempts
        else:  # linear
            delay = attempts

        # In real implementation, would sleep here
        # time.sleep(delay)

        return {**state, "attempts": attempts}

    return retry_node

def create_fallback_node(fallback_value: Any) -> Callable:
    """
    Create a fallback node that returns a fallback value

    Args:
        fallback_value: The value to return when recovery fails

    Returns:
        A node function that provides fallback
    """
    def fallback_node(state: dict) -> dict:
        """Fallback node that returns fallback value"""
        return {**state, "fallback_result": fallback_value, "error": None}

    return fallback_node

def error_boundary(recoverable: list = None):
    """
    Decorator to mark recoverable errors for a node

    Args:
        recoverable: List of exception types to treat as recoverable
    """
    if recoverable is None:
        recoverable = RECOVERABLE_ERRORS

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: dict) -> dict:
            try:
                return func(state)
            except Exception as e:
                if isinstance(e, tuple(recoverable)):
                    return {**state, "error": e, "recoverable": True}
                else:
                    raise
        return wrapper
    return decorator
