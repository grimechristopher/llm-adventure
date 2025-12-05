#!/usr/bin/env python3
"""
LLM Adventure CLI - Interactive menu-based world-building application
"""
import asyncio
import sys
import httpx
from rich.console import Console

from config import Config
from state import state
from display import (
    show_header,
    show_error,
    show_success,
    show_info,
    display_locations_table,
    display_facts_table,
)
from api_client import APIClient
from models import WorldCreate, WorldBuildingRequest

console = Console()


async def world_management_menu(config: Config):
    """World management submenu"""
    while True:
        show_header("World Management")

        console.print("1. Create New World")
        console.print("2. Select World")
        console.print("3. Back to Main Menu")

        choice = console.input("\n[cyan]Select option:[/cyan] ").strip()

        if choice == "1":
            await create_world_menu(config)
        elif choice == "2":
            await select_world_menu(config)
        elif choice == "3":
            break
        else:
            show_error("Invalid option")


async def create_world_menu(config: Config):
    """Create a new world"""
    show_header("Create New World")

    name = console.input("[cyan]World name:[/cyan] ").strip()
    if not name:
        show_error("World name cannot be empty")
        return

    description = console.input("[cyan]Description (optional):[/cyan] ").strip()
    user = console.input("[cyan]Created by (optional):[/cyan] ").strip()

    try:
        client = APIClient(config)
        world_data = WorldCreate(
            name=name,
            description=description if description else None,
            created_by_user=user if user else None,
        )

        show_info("Creating world...")
        result = await client.create_world(world_data)

        show_success(f"World created! ID: {result.id}")
        console.print(f"[dim]You can now select this world using ID: {result.id}[/dim]\n")

        # Optionally set as current world
        set_current = console.input("[cyan]Set as current world? (y/n):[/cyan] ").strip().lower()
        if set_current == "y":
            state.set_world(result.id, result.name)
            show_success(f"Current world set to: {result.name}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            show_error(f"Validation error: {e.response.text}")
        elif e.response.status_code >= 500:
            show_error("Server error - please try again later")
        else:
            show_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        show_error(f"Cannot connect to API at {config.api_base_url}")
        show_info("Make sure the API server is running (cd ../api && python run.py)")
    except httpx.TimeoutException:
        show_error("Request timed out - check API server")
    except Exception as e:
        show_error(f"Unexpected error: {e}")


async def select_world_menu(config: Config):
    """Select a world by ID"""
    show_header("Select World")

    world_id_str = console.input("[cyan]Enter world ID:[/cyan] ").strip()

    if not world_id_str.isdigit():
        show_error("World ID must be a number")
        return

    world_id = int(world_id_str)

    # Verify world exists by fetching locations
    try:
        client = APIClient(config)
        show_info("Verifying world...")
        await client.get_locations(world_id)

        # World exists, prompt for name
        world_name = console.input("[cyan]Enter world name (for display):[/cyan] ").strip()
        if not world_name:
            world_name = f"World {world_id}"

        state.set_world(world_id, world_name)
        show_success(f"Current world set to: {world_name}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            show_error(f"World {world_id} not found")
        else:
            show_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        show_error(f"Cannot connect to API at {config.api_base_url}")
    except Exception as e:
        show_error(f"Unexpected error: {e}")


async def world_building_menu(config: Config):
    """World building submenu"""
    show_header(f"Build {state.current_world_name}")

    console.print("[cyan]Enter a description of your world:[/cyan]")
    console.print(
        "[dim]Type your description, then press Ctrl+D (Unix) or Ctrl+Z (Windows) to finish[/dim]"
    )
    console.print(
        "[dim]Example: 'The village of Millbrook sits in a valley, population 200...'[/dim]\n"
    )

    # Multi-line input
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    description = "\n".join(lines).strip()

    if not description:
        show_error("No description provided")
        return

    try:
        client = APIClient(config)
        request = WorldBuildingRequest(
            world_id=state.current_world_id, description=description
        )

        console.print("\n[yellow]Processing description with LLM...[/yellow]")
        result = await client.describe_world(request)

        show_success(
            f"Created {result.locations_created} locations and {result.facts_created} facts"
        )

        if result.locations:
            console.print("\n[bold]Locations created:[/bold]")
            display_locations_table(result.locations)

        if result.facts:
            console.print("\n[bold]Facts extracted:[/bold]")
            display_facts_table(result.facts)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            show_error("World not found")
        elif e.response.status_code >= 500:
            show_error("Server error - please try again later")
        else:
            show_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        show_error(f"Cannot connect to API at {config.api_base_url}")
    except httpx.TimeoutException:
        show_error("Request timed out - LLM processing may take a while")
    except Exception as e:
        show_error(f"Unexpected error: {e}")

    console.print()  # Extra spacing


async def view_data_menu(config: Config):
    """View world data submenu"""
    while True:
        show_header(f"View Data: {state.current_world_name}")

        console.print("1. View Locations")
        console.print("2. View Facts")
        console.print("3. Back to Main Menu")

        choice = console.input("\n[cyan]Select option:[/cyan] ").strip()

        if choice == "1":
            await view_locations(config)
        elif choice == "2":
            await view_facts(config)
        elif choice == "3":
            break
        else:
            show_error("Invalid option")


async def view_locations(config: Config):
    """View all locations for current world"""
    try:
        client = APIClient(config)
        show_info("Fetching locations...")
        result = await client.get_locations(state.current_world_id)

        if result.count == 0:
            show_info("No locations found. Use World Building to add content.")
        else:
            display_locations_table(result.locations)

    except httpx.HTTPStatusError as e:
        show_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        show_error(f"Cannot connect to API at {config.api_base_url}")
    except Exception as e:
        show_error(f"Unexpected error: {e}")

    console.print()  # Extra spacing


async def view_facts(config: Config):
    """View all facts for current world"""
    try:
        client = APIClient(config)
        show_info("Fetching facts...")
        result = await client.get_facts(state.current_world_id)

        if result.count == 0:
            show_info("No facts found. Use World Building to add content.")
        else:
            display_facts_table(result.facts)

    except httpx.HTTPStatusError as e:
        show_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        show_error(f"Cannot connect to API at {config.api_base_url}")
    except Exception as e:
        show_error(f"Unexpected error: {e}")

    console.print()  # Extra spacing



async def main_menu():
    """Main menu loop"""
    config = Config.load()

    while True:
        show_header("LLM Adventure - Main Menu")

        if state.has_world_selected:
            console.print(
                f"[green]Current World:[/green] {state.current_world_name} (ID: {state.current_world_id})\n"
            )

        console.print("1. World Management")
        console.print(
            "2. World Building"
            + (
                " [dim](select world first)[/dim]"
                if not state.has_world_selected
                else ""
            )
        )
        console.print(
            "3. View World Data"
            + (
                " [dim](select world first)[/dim]"
                if not state.has_world_selected
                else ""
            )
        )
        console.print("4. Exit")

        choice = console.input("\n[cyan]Select option:[/cyan] ").strip()

        if choice == "1":
            await world_management_menu(config)
        elif choice == "2":
            if state.has_world_selected:
                await world_building_menu(config)
            else:
                show_error("Please select a world first (World Management → Select World)")
        elif choice == "3":
            if state.has_world_selected:
                await view_data_menu(config)
            else:
                show_error("Please select a world first (World Management → Select World)")
        elif choice == "4":
            console.print("[yellow]Goodbye![/yellow]")
            break
        else:
            show_error("Invalid option")


if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)
