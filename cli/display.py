"""
Display utilities using Rich library for beautiful terminal output
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import List
from models import LocationData, FactData

console = Console()


def show_header(title: str):
    """Display a header panel"""
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))


def show_error(message: str):
    """Display error message"""
    console.print(f"[bold red]Error:[/bold red] {message}")


def show_success(message: str):
    """Display success message"""
    console.print(f"[bold green]Success:[/bold green] {message}")


def show_info(message: str):
    """Display info message"""
    console.print(f"[cyan]{message}[/cyan]")


def display_locations_table(locations: List[LocationData]):
    """Display locations as a formatted table"""
    table = Table(title="Locations", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Relative Position", style="yellow")
    table.add_column("Elevation", justify="right")

    for loc in locations:
        table.add_row(
            str(loc.id),
            loc.name,
            loc.location_type or "-",
            loc.relative_position or "-",
            f"{loc.elevation_meters}m" if loc.elevation_meters else "-",
        )

    console.print(table)


def display_facts_table(facts: List[FactData]):
    """Display facts as a formatted table"""
    table = Table(title="Facts", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Category", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Content", style="white", max_width=60)

    for fact in facts:
        table.add_row(str(fact.id), fact.fact_category, fact.what_type or "-", fact.content)

    console.print(table)
