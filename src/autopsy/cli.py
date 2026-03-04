from pathlib import Path

import typer
from rich.console import Console

from autopsy import __version__

app = typer.Typer(help="code-autopsy: static analysis and debt scoring for Python projects.")
console = Console()


@app.callback()
def _main() -> None:
    pass


@app.command()
def scan(
    path: Path = typer.Argument(..., help="Root directory to scan."),
    config: Path = typer.Option(Path(".autopsy.toml"), "--config", help="Path to config file."),
) -> None:
    """Scan a directory for code quality issues."""
    console.print(f"[bold]code-autopsy[/bold] v{__version__}")
    console.print(f"Scanning [cyan]{path}[/cyan]...")
