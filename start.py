#!/usr/bin/env python3
import os
import sys
import time
import socket
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table

console = Console()

def check_system():
    """Check system requirements and port availability"""
    checks = [
        ("Checking Python version", lambda: sys.version_info >= (3, 7)),
        ("Checking port 5000", lambda: not is_port_in_use(5000)),
        ("Checking downloads directory", check_downloads_dir),
        ("Checking dependencies", check_dependencies)
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for desc, check_func in checks:
            task = progress.add_task(desc, total=None)
            time.sleep(0.5)  # For visual effect
            if not check_func():
                progress.stop()
                console.print(f"[red]✗ Failed: {desc}[/red]")
                return False
            progress.update(task, completed=True)
    return True

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_downloads_dir():
    downloads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
    if not os.path.exists(downloads_path):
        try:
            os.makedirs(downloads_path)
        except:
            return False
    return True

def check_dependencies():
    try:
        import flask
        import flask_socketio
        import yt_dlp
        import requests
        return True
    except ImportError:
        return False

def show_startup_banner():
    """Display a fancy startup banner"""
    banner = Panel.fit(
        "[bold green]BunnyCDN Downloader[/bold green]\n"
        "[blue]Created by MrGadhvii[/blue]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(banner)

def show_server_info():
    """Display server information in a table"""
    table = Table(show_header=False, border_style="green")
    table.add_row("[yellow]Server URL[/yellow]", "http://localhost:5000")
    table.add_row("[yellow]Version[/yellow]", "1.0.0")
    table.add_row("[yellow]Author[/yellow]", "MrGadhvii")
    console.print(table)

def main():
    try:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Show banner
        show_startup_banner()
        
        # System checks
        console.print("\n[yellow]Performing system checks...[/yellow]")
        if not check_system():
            console.print("\n[red]System checks failed. Please fix the issues and try again.[/red]")
            return
        
        console.print("\n[green]✓ All checks passed![/green]")
        
        # Show server info
        console.print("\n[yellow]Server Information:[/yellow]")
        show_server_info()
        
        # Start the server
        console.print("\n[green]Starting server...[/green]")
        from bunny_analyzer import app, socketio
        
        # Run the application
        console.print("\n[green]Server is running![/green]")
        console.print("[blue]Press Ctrl+C to stop the server[/blue]")
        socketio.run(app, host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    main()
