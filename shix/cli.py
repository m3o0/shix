"""shix CLI — find shell commands using natural language."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from shix import __version__
from shix.history import read_history
from shix.sanitize import sanitize

app = typer.Typer(
    name="shix",
    help="Find and run shell commands using natural language.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@dataclass
class DisplayItem:
    command: str
    explanation: str


def _copy_to_clipboard(text: str) -> bool:
    """Try to copy text to clipboard. Returns True on success."""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        return False


def _display_and_pick(items: list[DisplayItem]) -> None:
    """Display suggestions with rich formatting and copy-to-clipboard prompt."""
    if not items:
        console.print("[yellow]No suggestions found. Try rephrasing your query.[/yellow]")
        return

    console.print()
    for i, item in enumerate(items, 1):
        panel = Panel(
            Text(item.command, style="bold green"),
            title=f"[bold cyan]#{i}[/bold cyan]",
            subtitle=Text(item.explanation, style="dim"),
            border_style="cyan",
            padding=(0, 2),
        )
        console.print(panel)

    console.print()

    try:
        choice = typer.prompt(
            f"Copy command to clipboard (1-{len(items)}, or Enter to skip)",
            default="",
            show_default=False,
        )
    except (KeyboardInterrupt, EOFError):
        console.print()
        return

    if choice.isdigit() and 1 <= int(choice) <= len(items):
        cmd = items[int(choice) - 1].command
        if _copy_to_clipboard(cmd):
            console.print(f"[green]Copied to clipboard:[/green] {cmd}")
        else:
            console.print(f"[yellow]Could not copy. Here's the command:[/yellow]\n{cmd}")


@app.command()
def ask(
    query: str = typer.Argument(..., help="Describe what you want to do"),
    local: bool = typer.Option(False, "--local", "-l", help="Use local Ollama model instead of offline search"),
    model: str = typer.Option("qwen2.5:7b", "--model", "-m", help="Ollama model (only with --local)"),
    base_url: str = typer.Option("http://localhost:11434", "--url", "-u", help="Ollama server URL (only with --local)"),
    history_lines: int = typer.Option(0, "--history", "-n", help="Number of history lines to read (0 = all)"),
) -> None:
    """Describe what you want to do and get command suggestions."""
    # 1. Read history
    with console.status("[bold cyan]Reading shell history..."):
        history = read_history(max_lines=history_lines)

    if not history:
        console.print("[yellow]No shell history found.[/yellow]")
        if local:
            console.print("[yellow]Suggestions may be less personalized.[/yellow]")
            history = []
        else:
            console.print("[yellow]Offline mode needs history to search. Try --local for AI suggestions.[/yellow]")
            raise typer.Exit(1)

    # 2. Sanitize (needed for --local to avoid sending secrets)
    clean_history = sanitize(history)

    if local:
        _run_local(clean_history, query, model, base_url)
    else:
        _run_offline(history, query)


def _run_offline(history: list[str], query: str) -> None:
    """Fuzzy search through history — no model, instant results."""
    from shix.fuzzy import fuzzy_search, _tokenize

    results = fuzzy_search(history, query)

    # Show which query tokens had zero matches across all history
    if results:
        query_tokens = _tokenize(query)
        history_blob = " ".join(history).lower()
        missing = [t for t in query_tokens if t not in history_blob]
        if missing:
            console.print(f"[dim]No history matches for: {', '.join(missing)}[/dim]")

    items = [
        DisplayItem(command=r.command, explanation=r.reason)
        for r in results
    ]
    _display_and_pick(items)


def _run_local(history: list[str], query: str, model: str, base_url: str) -> None:
    """Query local Ollama model for suggestions."""
    try:
        from shix.ollama import get_suggestions
    except ImportError:
        console.print(
            "[red]Missing dependency for --local mode.[/red]\n"
            "Install with: [bold]pip install shix\\[local][/bold]  (or: pip install httpx)"
        )
        raise typer.Exit(1)

    with console.status("[bold cyan]Thinking..."):
        try:
            suggestions = get_suggestions(
                history=history,
                query=query,
                model=model,
                base_url=base_url,
            )
        except Exception as e:
            error_msg = str(e)
            if "ConnectError" in type(e).__name__ or "Connection" in error_msg:
                console.print(
                    "[red]Could not connect to Ollama.[/red]\n"
                    "Make sure Ollama is running: [bold]ollama serve[/bold]\n"
                    f"And that the model is pulled: [bold]ollama pull {model}[/bold]"
                )
            else:
                console.print(f"[red]Error: {error_msg}[/red]")
            raise typer.Exit(1)

    items = [
        DisplayItem(command=s.command, explanation=s.explanation)
        for s in suggestions
    ]
    _display_and_pick(items)


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
