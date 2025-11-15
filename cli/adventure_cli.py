#!/usr/bin/env python3
"""
LLM Adventure CLI

A command-line interface for interacting with the LLM Adventure API.
"""

import requests
import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

console = Console()

class APIClient:
    """Client for interacting with the LLM Adventure API"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv('API_URL', 'http://127.0.0.1:5000')
        self.session = requests.Session()
        
    def make_request(self, method, endpoint, **kwargs):
        """Make a request to the API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            console.print(f"[red]Error: Could not connect to API at {self.base_url}[/red]")
            console.print("[yellow]Make sure the API server is running![/yellow]")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]HTTP Error: {e}[/red]")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Request Error: {e}[/red]")
            return None
    
    def get_welcome(self):
        """Get welcome message from API"""
        return self.make_request('GET', '/')
    
    def get_health(self):
        """Get health status from API"""
        return self.make_request('GET', '/health')

@click.group()
@click.option('--api-url', default='http://127.0.0.1:5000', help='API base URL')
@click.pass_context
def cli(ctx, api_url):
    """LLM Adventure CLI - Interact with the adventure game API"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = APIClient(api_url)

@cli.command()
@click.pass_context
def status(ctx):
    """Check API status and health"""
    client = ctx.obj['client']
    
    console.print(Panel("[bold blue]API Status Check[/bold blue]", expand=False))
    
    # Check welcome endpoint
    welcome_data = client.get_welcome()
    if welcome_data:
        console.print("[green]✓[/green] API is responding")
        rprint(f"  Message: {welcome_data.get('message', 'N/A')}")
        rprint(f"  Status: {welcome_data.get('status', 'N/A')}")
    
    # Check health endpoint
    health_data = client.get_health()
    if health_data:
        console.print("[green]✓[/green] Health check passed")
        rprint(f"  Service: {health_data.get('service', 'N/A')}")
        rprint(f"  Version: {health_data.get('version', 'N/A')}")

@cli.command()
@click.pass_context
def info(ctx):
    """Get API information"""
    client = ctx.obj['client']
    
    data = client.get_welcome()
    if data:
        # Create a nice table
        table = Table(title="API Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Message", data.get('message', 'N/A'))
        table.add_row("Status", data.get('status', 'N/A'))
        table.add_row("Description", data.get('description', 'N/A'))
        table.add_row("API URL", client.base_url)
        
        console.print(table)

@cli.command()
@click.option('--endpoint', '-e', help='API endpoint to call (e.g., /health)')
@click.option('--method', '-m', default='GET', help='HTTP method (GET, POST, etc.)')
@click.option('--data', '-d', help='JSON data for POST requests')
@click.pass_context
def request(ctx, endpoint, method, data):
    """Make a custom request to the API"""
    if not endpoint:
        console.print("[red]Error: Please specify an endpoint with --endpoint[/red]")
        return
    
    client = ctx.obj['client']
    
    kwargs = {}
    if data and method.upper() in ['POST', 'PUT', 'PATCH']:
        import json
        try:
            kwargs['json'] = json.loads(data)
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON data[/red]")
            return
    
    result = client.make_request(method.upper(), endpoint, **kwargs)
    if result:
        console.print(Panel(f"[bold green]Response from {endpoint}[/bold green]"))
        rprint(result)

@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive mode"""
    client = ctx.obj['client']
    
    console.print(Panel("[bold cyan]LLM Adventure Interactive Mode[/bold cyan]"))
    console.print("Type 'help' for available commands, 'exit' to quit")
    
    while True:
        try:
            command = input("\n> ").strip().lower()
            
            if command in ['exit', 'quit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif command in ['help', '?']:
                console.print("\n[cyan]Available commands:[/cyan]")
                console.print("  status  - Check API status")
                console.print("  info    - Get API information")
                console.print("  health  - Check health endpoint")
                console.print("  welcome - Get welcome message")
                console.print("  help    - Show this help")
                console.print("  exit    - Exit interactive mode")
            elif command == 'status':
                ctx.invoke(status)
            elif command == 'info':
                ctx.invoke(info)
            elif command == 'health':
                health_data = client.get_health()
                if health_data:
                    rprint(health_data)
            elif command == 'welcome':
                welcome_data = client.get_welcome()
                if welcome_data:
                    rprint(welcome_data)
            else:
                console.print(f"[red]Unknown command: {command}[/red]")
                console.print("Type 'help' for available commands")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break

if __name__ == '__main__':
    cli()