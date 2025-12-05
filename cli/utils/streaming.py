"""
Streaming response handlers for real-time display
"""
from typing import AsyncIterator
from rich.console import Console


async def display_stream(stream: AsyncIterator[str], console: Console):
    """
    Display streaming text in real-time

    Collects chunks and displays them as they arrive,
    providing a typewriter effect.
    """
    full_response = ""

    console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

    async for chunk in stream:
        full_response += chunk
        console.print(chunk, end="")

    console.print()  # Newline after stream completes
    return full_response
