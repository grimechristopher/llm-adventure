# tests/core/test_error_recovery.py
import pytest
from typing import TypedDict

class TestState(TypedDict):
    value: int
    error: Exception | None
    attempts: int

def test_create_retry_node_retries_on_failure():
    """Test retry node increments attempts"""
    from core.error_recovery import create_retry_node

    retry_node = create_retry_node(max_attempts=3)

    state = TestState(value=0, error=Exception("test"), attempts=1)
    result = retry_node(state)

    assert result["attempts"] == 2

def test_create_fallback_node_returns_fallback_value():
    """Test fallback node returns fallback when max attempts reached"""
    from core.error_recovery import create_fallback_node

    fallback_node = create_fallback_node(fallback_value="fallback")

    state = TestState(value=0, error=Exception("test"), attempts=3)
    result = fallback_node(state)

    assert "fallback_result" in result
    assert result["fallback_result"] == "fallback"

def test_is_recoverable_error_identifies_recoverable():
    """Test is_recoverable identifies tool and validation errors"""
    from core.error_recovery import is_recoverable, ToolError, ValidationError

    assert is_recoverable(ToolError("test")) is True
    assert is_recoverable(ValidationError("test")) is True
    assert is_recoverable(RuntimeError("test")) is False
