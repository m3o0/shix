"""shix CLI — find shell commands using natural language."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import typer
from rich.console import Console
from rich.padding import Padding
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

BORDER_STYLE = "bright_black"


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


def _make_chip(text: str, index: int) -> tuple[str, str, str]:
    """Create a single chip/pill string with box-drawing characters."""
    label = f" {index}  {text} "
    top = f"╭{'─' * len(label)}╮"
    mid = f"│{label}│"
    bot = f"╰{'─' * len(label)}╯"
    return top, mid, bot


def _truncate_cmd(cmd: str, max_width: int = 50) -> str:
    """Truncate a command for chip display."""
    display = cmd.split("\n")[0]
    if len(display) > max_width:
        display = display[:max_width - 1] + "…"
    return display


def _render_chips(items: list[DisplayItem]) -> None:
    """Render command suggestions as chips/pills in rows."""
    if not items:
        return

    width = console.width - 4  # padding
    display_cmds = [_truncate_cmd(item.command) for item in items]
    chips = [_make_chip(dc, i + 1) for i, dc in enumerate(display_cmds)]

    # Group chips into rows that fit terminal width
    rows: list[list[int]] = []
    current_row: list[int] = []
    current_width = 0

    for i, (top, mid, bot) in enumerate(chips):
        chip_width = len(mid) + 2  # +2 for spacing between chips
        if current_row and current_width + chip_width > width:
            rows.append(current_row)
            current_row = [i]
            current_width = len(mid)
        else:
            current_row.append(i)
            current_width += chip_width

    if current_row:
        rows.append(current_row)

    # Render each row
    for row in rows:
        top_line = "  "
        bot_line = "  "
        for idx in row:
            t, m, b = chips[idx]
            top_line += t + "  "
            bot_line += b + "  "

        console.print(Text(top_line, style=BORDER_STYLE))
        console.print(_style_mid_line(display_cmds, row))
        console.print(Text(bot_line, style=BORDER_STYLE))


def _render_compact(items: list[DisplayItem]) -> None:
    """Render commands as a compact numbered list for many results."""
    idx_width = len(str(len(items)))
    max_cmd = console.width - idx_width - 8
    for i, item in enumerate(items, 1):
        display = _truncate_cmd(item.command, max_cmd)
        line = Text("  ")
        line.append(f" {i:>{idx_width}} ", style="bold yellow")
        line.append(f" {display}", style="bold white")
        console.print(line)



def _style_mid_line(display_cmds: list[str], row_indices: list[int]) -> Text:
    """Style the middle line of chips with colored numbers and commands."""
    result = Text()
    result.append("  ", style="")

    for idx in row_indices:
        num = str(idx + 1)
        cmd = display_cmds[idx]
        result.append("│", style=BORDER_STYLE)
        result.append(f" {num} ", style="bold yellow")
        result.append(f" {cmd} ", style="bold white")
        result.append("│", style=BORDER_STYLE)
        result.append("  ", style="")

    return result


def _render_header(query: str, mode: str, missing_tokens: list[str] | None = None) -> None:
    """Render the shix header with query context."""
    console.print()
    header = Text("  shix", style="bold cyan")
    header.append("  ", style="dim")
    header.append(mode, style="dim italic")
    console.print(header)
    console.print()

    query_line = Text("  ")
    query_line.append("> ", style="bold cyan")
    query_line.append(query, style="bold white")
    console.print(query_line)

    if missing_tokens:
        warn = Text("    no history for: ", style="dim")
        warn.append(", ".join(missing_tokens), style="yellow")
        console.print(warn)

    console.print()


def _display_and_pick(items: list[DisplayItem], query: str, mode: str, missing_tokens: list[str] | None = None) -> None:
    """Display suggestions as chips and prompt for selection."""
    _render_header(query, mode, missing_tokens)

    if not items:
        console.print(Padding(
            Text("No matches found. Try different keywords.", style="yellow"),
            (0, 4),
        ))
        console.print()
        return

    if len(items) <= 5:
        _render_chips(items)
    else:
        _render_compact(items)

    # Separator + prompt
    console.print()
    console.print(Text("  " + "─" * (console.width - 4), style=BORDER_STYLE))
    console.print()

    try:
        prompt_text = Text("  ")
        prompt_text.append("Pick ", style="dim")
        prompt_text.append(f"[1-{len(items)}]", style="bold yellow")
        prompt_text.append(" to copy, ", style="dim")
        prompt_text.append("Enter", style="dim bold")
        prompt_text.append(" to skip", style="dim")
        console.print(prompt_text, end="")

        choice = input("  ")
    except (KeyboardInterrupt, EOFError):
        console.print()
        return

    choice = choice.strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        cmd = items[int(choice) - 1].command
        if _copy_to_clipboard(cmd):
            console.print()
            copied = Text("  ")
            copied.append(" COPIED ", style="bold black on green")
            copied.append(f"  {cmd}", style="green")
            console.print(copied)
        else:
            console.print()
            console.print(Padding(Text(cmd, style="bold white"), (0, 4)))

    console.print()


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
        DisplayItem(command=r.command, explanation=r.reason)
        for r in results
    ]
    _display_and_pick(items, query, "offline", missing if missing else None)


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
        DisplayItem(command=s.command, explanation=s.explanation)
        for s in suggestions
    ]
    _display_and_pick(items, query, f"local ({model})")


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
