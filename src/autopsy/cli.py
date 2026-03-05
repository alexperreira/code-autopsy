from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from autopsy import __version__
from autopsy.analyzers.python import PythonAnalyzer
from autopsy.config import load_config
from autopsy.scanner import scan_files

app = typer.Typer(help="code-autopsy: static analysis and debt scoring for Python projects.")
console = Console()

_python_analyzer = PythonAnalyzer()


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

    cfg = load_config(config)

    results = []
    for filepath in scan_files(path, cfg):
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            console.print(f"[yellow]Warning:[/yellow] cannot read {filepath}: {exc}", err=True)
            continue
        results.append(_python_analyzer.analyze(filepath, source, cfg))

    if not results:
        console.print("[yellow]No Python files found.[/yellow]")
        return

    table = Table(title="Scan Results", show_lines=False)
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Functions", justify="right")
    table.add_column("Max CC", justify="right")
    table.add_column("Issues", justify="right")

    root = path.resolve()
    for result in sorted(results, key=lambda r: r.path):
        try:
            display_path = result.path.relative_to(root)
        except ValueError:
            display_path = result.path

        max_cc = result.metrics.max_cyclomatic
        cc_str = f"[red]{max_cc}[/red]" if max_cc >= cfg.thresholds.max_cyclomatic_complexity else str(max_cc)

        issue_count = len(result.issues)
        issue_str = f"[red]{issue_count}[/red]" if issue_count else "0"

        table.add_row(
            str(display_path),
            str(result.metrics.function_count),
            cc_str,
            issue_str,
        )

    console.print(table)
    console.print(f"[bold]Total files:[/bold] {len(results)}")
