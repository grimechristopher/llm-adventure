"""
DeepAgent Configuration for LLM-Adventure

This module provides factory functions for creating DeepAgents with
appropriate backends and configurations for the llm-adventure project.
"""

from deepagents import create_deep_agent
from deepagents.backends import StateBackend, FilesystemBackend
from typing import List, Optional
from langchain_core.tools import BaseTool


def get_deepagent_backend(backend_type: str = 'state'):
    """
    Factory for DeepAgent backends.

    Args:
        backend_type: Type of backend to use ('state' or 'filesystem')

    Returns:
        Backend instance

    Raises:
        ValueError: If unknown backend type specified
    """
    if backend_type == 'state':
        # Ephemeral state backend - good for testing and short sessions
        # No persistence across restarts
        return StateBackend()
    elif backend_type == 'filesystem':
        # Persistent filesystem backend - good for long-running tasks
        # Survives restarts, allows inspection of agent state
        return FilesystemBackend(base_dir='./deepagent_workspace')
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")


def create_llm_adventure_agent(
    tools: List[BaseTool],
    system_prompt: str,
    model_name: Optional[str] = None,
    backend_type: str = 'state'
):
    """
    Create DeepAgent with llm-adventure defaults.

    This is the standard factory for creating agents in the llm-adventure project.
    Uses StateBackend by default for fast iteration and testing.

    Args:
        tools: List of LangChain tools available to the agent
        system_prompt: System prompt defining agent behavior
        model_name: Optional model identifier (None uses Claude Sonnet 4.5 default)
        backend_type: Backend type ('state' or 'filesystem')

    Returns:
        Configured DeepAgent instance ready for invocation

    Example:
        >>> from tools import WORLD_BUILDING_TOOLS
        >>> agent = create_llm_adventure_agent(
        ...     tools=WORLD_BUILDING_TOOLS,
        ...     system_prompt="You are a world-building assistant...",
        ...     model_name=None  # Uses default
        ... )
        >>> result = agent.invoke({"messages": [{"role": "user", "content": "Build a world"}]})
    """
    backend = get_deepagent_backend(backend_type)

    return create_deep_agent(
        tools=tools,
        system_prompt=system_prompt,
        model=model_name,  # None = uses Claude Sonnet 4.5 default from DeepAgents
        backend=backend
    )
