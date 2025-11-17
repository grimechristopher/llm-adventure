#!/usr/bin/env python3
"""
Direct CLI Chat - Tests the agent and database directly without HTTP layer

This script:
- Uses the same LLM setup as the API (from config/llm.py)
- Tests database connection and chat history
- Runs interactive chat sessions
- Verifies that conversations are saved to PostgreSQL
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the api directory to Python path so we can import from it
api_dir = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich import print as rprint

# Import from the api module
from agents.simple_agent import chat_stream
from config.llm import initialize_llms
from config.database import (
    test_postgres_connection,
    initialize_database,
    get_chat_history,
    get_db_connection
)
from utils.logging import setup_logging, get_logger

# Load environment from api/.env
env_path = api_dir / ".env"
load_dotenv(env_path)

# Setup logging
setup_logging()

console = Console()
logger = get_logger(__name__)


def print_header():
    """Print welcome header"""
    header = """
    # 🎮 LLM Adventure - Direct Chat CLI

    Testing the agent and database directly (no HTTP layer)
    """
    console.print(Panel(Markdown(header), style="bold cyan"))


async def test_database():
    """
    Test database connection and initialization

    Returns True if successful, False otherwise
    """
    console.print("\n[cyan]Testing database connection...[/cyan]")

    # Test basic connection
    if not test_postgres_connection():
        console.print("[red]✗[/red] Database connection failed!")
        console.print("\n[yellow]Make sure PostgreSQL is running and configured in api/.env[/yellow]")
        return False

    console.print("[green]✓[/green] Database connection successful")

    # Initialize tables
    console.print("[cyan]Initializing database tables...[/cyan]")
    if not await initialize_database():
        console.print("[red]✗[/red] Failed to initialize database tables")
        return False

    console.print("[green]✓[/green] Database tables initialized")
    return True


async def view_conversation_history(session_id: str):
    """View the conversation history for a session from the database"""
    console.print(f"\n[cyan]Conversation history for session: {session_id}[/cyan]")

    try:
        history = get_chat_history(session_id)
        messages = history.messages

        if not messages:
            console.print("[yellow]No messages in this session yet[/yellow]")
            return

        console.print(f"\n[green]Found {len(messages)} messages:[/green]\n")

        for i, msg in enumerate(messages, 1):
            role = msg.__class__.__name__.replace("Message", "")
            console.print(f"[bold]{i}. {role}:[/bold]")
            console.print(f"   {msg.content}\n")

    except Exception as e:
        console.print(f"[red]Error viewing history: {e}[/red]")


async def list_sessions():
    """List all chat sessions in the database"""
    console.print("\n[cyan]Listing all chat sessions...[/cyan]")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query distinct session IDs from the chat_message_history table
        cursor.execute("""
            SELECT DISTINCT session_id, COUNT(*) as message_count,
                   MIN(created_at) as first_message,
                   MAX(created_at) as last_message
            FROM chat_message_history
            GROUP BY session_id
            ORDER BY last_message DESC
        """)

        sessions = cursor.fetchall()
        cursor.close()

        if not sessions:
            console.print("[yellow]No sessions found in database[/yellow]")
            return

        console.print(f"\n[green]Found {len(sessions)} session(s):[/green]\n")

        from rich.table import Table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Session ID", style="cyan")
        table.add_column("Messages", justify="right")
        table.add_column("First Message", style="dim")
        table.add_column("Last Message", style="dim")

        for session_id, count, first, last in sessions:
            table.add_row(
                session_id,
                str(count),
                str(first) if first else "N/A",
                str(last) if last else "N/A"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing sessions: {e}[/red]")


async def chat_interactive(llm, session_id: str):
    """
    Run an interactive chat session

    Args:
        llm: The language model instance
        session_id: Session ID for conversation history
    """
    console.print(f"\n[green]Starting chat session: {session_id}[/green]")
    console.print("[dim]Type 'exit' to quit, 'history' to view conversation, 'sessions' to list all sessions[/dim]\n")

    while True:
        # Get user input
        try:
            user_message = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if not user_message.strip():
                continue

            # Handle special commands
            if user_message.lower() in ['exit', 'quit', 'q']:
                console.print("\n[yellow]Goodbye![/yellow]")
                break

            if user_message.lower() == 'history':
                await view_conversation_history(session_id)
                continue

            if user_message.lower() == 'sessions':
                await list_sessions()
                continue

            # Stream the response
            console.print("\n[bold green]Assistant[/bold green]: ", end="")

            response_text = ""
            async for chunk in chat_stream(llm, user_message, session_id):
                console.print(chunk, end="")
                response_text += chunk

            console.print()  # New line after response

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Goodbye![/yellow]")
            break
        except EOFError:
            console.print("\n\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.error("Chat error", error=str(e))


async def main():
    """Main entry point"""
    print_header()

    # Test database
    if not await test_database():
        console.print("\n[red]Cannot continue without database connection[/red]")
        return 1

    # Setup LLMs using the same initialization as the API
    console.print("\n[cyan]Initializing LLMs...[/cyan]")
    llms = initialize_llms()

    if not llms:
        console.print("[red]✗[/red] No LLMs could be initialized!")
        return 1

    # Use lm_studio by default (same as the API does)
    llm = llms.get('lm_studio') or llms.get('azure_one')

    if not llm:
        console.print("[red]✗[/red] No suitable LLM found!")
        return 1

    llm_name = 'lm_studio' if 'lm_studio' in llms else 'azure_one'
    console.print(f"[green]✓[/green] Using LLM: {llm_name}")

    # Get session ID from user
    console.print("\n[cyan]Enter a session ID (or press Enter for 'default'):[/cyan]")
    session_id = Prompt.ask("Session ID", default="default")

    # Check if session has existing history
    try:
        history = get_chat_history(session_id)
        message_count = len(history.messages)
        if message_count > 0:
            console.print(f"\n[yellow]This session has {message_count} existing messages[/yellow]")
            view_history = Prompt.ask("View history before starting?", choices=["y", "n"], default="n")
            if view_history == "y":
                await view_conversation_history(session_id)
    except Exception as e:
        console.print(f"[yellow]Note: Could not load history: {e}[/yellow]")

    # Start interactive chat
    await chat_interactive(llm, session_id)

    # Show final history
    console.print("\n[cyan]Session complete![/cyan]")
    show_final = Prompt.ask("View final conversation history?", choices=["y", "n"], default="y")
    if show_final == "y":
        await view_conversation_history(session_id)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
