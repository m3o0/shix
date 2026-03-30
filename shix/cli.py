"""shix CLI — find shell commands using natural language."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from shix import __version__
from shix.history import read_history
from shix.tui import SuggestionItem, run_tui


app = typer.Typer(
    name="shix",
    help="Find and run shell commands using natural language.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.command()
def ask(
    query: str = typer.Argument(..., help="Describe what you want to do"),
    top: int = typer.Option(5, "--top", "-t", help="Number of suggestions to show"),
    history_lines: int = typer.Option(0, "--history", "-n", help="Number of history lines to read (0 = all)"),
) -> None:
    """Describe what you want to do and get command suggestions."""
    with console.status("[bold cyan]  Reading shell history..."):
        history, freq = read_history(max_lines=history_lines)

    if not history:
        console.print("[yellow]  No shell history found.[/yellow]")
        raise typer.Exit(1)

    from shix.fuzzy import fuzzy_search, _tokenize

    results = fuzzy_search(history, query, max_results=top, freq=freq)

    query_tokens = _tokenize(query)
    history_blob = " ".join(history).lower()
    missing = [t for t in query_tokens if t not in history_blob]

    items = [
        SuggestionItem(command=r.command, explanation=r.reason)
        for r in results
    ]

    result, clipboard_ok = run_tui(items, query, "search", missing if missing else None)

    # Reset bracketed paste mode that Textual may leave enabled
    import sys
    sys.stdout.write("\033[?2004l")
    sys.stdout.flush()

    if result:
        hint = "Paste with Ctrl+V / Cmd+V to run" if clipboard_ok else "Copy the command above to run"
        console.print(f"\n  {result}\n\n  [dim]{hint}[/dim]")


@app.callback(invoke_without_command=True)
def main(
    version: Optional[bool] = typer.Option(None, "--version", "-v", help="Show version", is_eager=True),
) -> None:
    """shix — find shell commands using natural language."""
    if version:
        console.print(f"shix {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
