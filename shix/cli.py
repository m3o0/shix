"""shix CLI — find shell commands using natural language."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from shix import __version__
from shix.history import read_history
from shix.sanitize import sanitize
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
    local: bool = typer.Option(False, "--local", "-l", help="Use local Ollama model instead of offline search"),
    model: str = typer.Option("qwen2.5:7b", "--model", "-m", help="Ollama model (only with --local)"),
    base_url: str = typer.Option("http://localhost:11434", "--url", "-u", help="Ollama server URL (only with --local)"),
    history_lines: int = typer.Option(0, "--history", "-n", help="Number of history lines to read (0 = all)"),
) -> None:
    """Describe what you want to do and get command suggestions."""
    with console.status("[bold cyan]  Reading shell history..."):
        history = read_history(max_lines=history_lines)

    if not history:
        console.print("[yellow]  No shell history found.[/yellow]")
        if local:
            history = []
        else:
            console.print("[yellow]  Offline mode needs history. Try --local for AI suggestions.[/yellow]")
            raise typer.Exit(1)

    clean_history = sanitize(history)

    if local:
        _run_local(clean_history, query, model, base_url, top)
    else:
        _run_offline(history, query, top)


def _run_offline(history: list[str], query: str, top: int = 5) -> None:
    """Fuzzy search through history — no model, instant results."""
    from shix.fuzzy import fuzzy_search, _tokenize

    results = fuzzy_search(history, query, max_results=top)

    query_tokens = _tokenize(query)
    history_blob = " ".join(history).lower()
    missing = [t for t in query_tokens if t not in history_blob]

    items = [
        SuggestionItem(command=r.command, explanation=r.reason)
        for r in results
    ]

    result, clipboard_ok = run_tui(items, query, "offline", missing if missing else None)
    if result:
        hint = "Paste with Ctrl+V / Cmd+V to run" if clipboard_ok else "Copy the command above to run"
        console.print(f"\n  {result}\n\n  [dim]{hint}[/dim]")


def _run_local(history: list[str], query: str, model: str, base_url: str, top: int = 5) -> None:
    """Query local Ollama model for suggestions."""
    try:
        from shix.ollama import get_suggestions
    except ImportError:
        console.print(
            "[red]  Missing dependency for --local mode.[/red]\n"
            "  Install with: [bold]pip install shix\\[local][/bold]  (or: pip install httpx)"
        )
        raise typer.Exit(1)

    with console.status("[bold cyan]  Thinking..."):
        try:
            suggestions = get_suggestions(
                history=history,
                query=query,
                model=model,
                base_url=base_url,
                count=top,
            )
        except Exception as e:
            error_msg = str(e)
            if "ConnectError" in type(e).__name__ or "Connection" in error_msg:
                console.print(
                    "[red]  Could not connect to Ollama.[/red]\n"
                    "  Make sure Ollama is running: [bold]ollama serve[/bold]\n"
                    f"  And that the model is pulled: [bold]ollama pull {model}[/bold]"
                )
            else:
                console.print(f"[red]  Error: {error_msg}[/red]")
            raise typer.Exit(1)

    items = [
        SuggestionItem(command=s.command, explanation=s.explanation)
        for s in suggestions
    ]

    result, clipboard_ok = run_tui(items, query, f"local ({model})")
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
