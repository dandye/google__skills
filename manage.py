#!/usr/bin/env python3
"""
Unified CLI for google__skills

Entrypoint for CLI commands, service operations, and development workflows.
"""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console


# Resolve root relative to this file for cross-worktree portability
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

console = Console()

app = typer.Typer(
    name="google--skills",
    help="Unified management CLI for google__skills",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    """google__skills CLI Operations."""
    pass


@app.command("info")
def info() -> None:
    """Display project configuration and environment status."""
    console.print("[bold blue]google__skills[/bold blue] Environment Status")
    console.print(f"Base Directory: [cyan]{BASE_DIR}[/cyan]")


@app.command("run-demo")
def run_demo(
    name: Annotated[
        str, typer.Option("--name", "-n", help="Target entity name")
    ] = "world",
) -> None:
    """Run basic demo pipeline."""
    from google__skills.core import run_pipeline

    result = run_pipeline(name)
    console.print(f"[green]Pipeline Output:[/green] {result}")


if __name__ == "__main__":
    app()
