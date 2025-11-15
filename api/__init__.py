"""
LLM Adventure API Package

This package contains the API components for the LLM Adventure game,
including routes, services, models, and configuration.
"""

from .app import create_app

__version__ = "1.0.0"
__author__ = "Chris Grime"

# Export the factory function, not an app instance
__all__ = ['create_app']