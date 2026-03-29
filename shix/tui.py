"""Textual TUI app for shix — interactive command suggestion browser."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widgets import Static, Label


@dataclass
class SuggestionItem:
    command: str
    explanation: str


class CommandPill(Static, can_focus=True):
    """A focusable pill-shaped command suggestion."""

    BINDINGS = [
        Binding("up,left,k", "app.focus_prev", show=False),
        Binding("down,right,j", "app.focus_next", show=False),
        Binding("enter", "app.select", show=False),
    ]

    class Selected(Message):
        def __init__(self, command: str) -> None:
            self.command = command
            super().__init__()

    def __init__(self, command: str, **kwargs) -> None:
        display = command.split("\n")[0]
        super().__init__(display, **kwargs)
        self.command = command

    def on_enter(self, event) -> None:
        self.focus(scroll_visible=False)

    def on_click(self) -> None:
        self.post_message(self.Selected(self.command))


class ResultRow(Horizontal):
    """A row containing an index label and a command pill."""

    DEFAULT_CSS = """
    ResultRow {
        height: 1;
        width: 100%;
        margin-bottom: 1;
    }
    """

    def on_enter(self, event) -> None:
        pill = self.query_one(CommandPill)
        pill.focus(scroll_visible=False)

    def on_click(self) -> None:
        pill = self.query_one(CommandPill)
        pill.post_message(CommandPill.Selected(pill.command))


class PillsContainer(Container, can_focus=False):
    """A container that does not capture key events."""

    DEFAULT_CSS = """
    PillsContainer {
        height: 1fr;
        overflow-y: auto;
    }
    """


class ShixApp(App):
    """Interactive command suggestion browser."""

    TITLE = "shix"
    COMMAND_PALETTE_BINDING = "ctrl+p"

    CSS = """
    Screen {
        background: #0d1117;
        padding: 1 2;
    }

    #title-text {
        color: #58a6ff;
        height: 1;
    }

    #query-text {
        color: #e6edf3;
        height: 1;
        margin-bottom: 1;
    }

    #warning {
        color: #d29922;
        height: 1;
        margin-top: 1;
        display: none;
    }

    #warning.visible {
        display: block;
    }

    #pills-label {
        color: #484f58;
        height: 1;
        margin-bottom: 1;
    }

    .pill-index {
        width: 4;
        height: 1;
        color: #484f58;
        padding: 0 1 0 0;
        content-align: right middle;
    }

    CommandPill {
        width: auto;
        height: 1;
        max-width: 1fr;
        padding: 0 2;
        color: #8b949e;
        background: #21262d;
    }

    CommandPill:hover {
        background: #30363d;
        color: #c9d1d9;
    }

    CommandPill:focus {
        background: #1f6feb;
        color: #ffffff;
        text-style: bold;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #010409;
        color: #484f58;
        padding: 0 2;
    }

    #status-bar.copied {
        background: #238636;
        color: #ffffff;
        text-style: bold;
    }

    Footer {
        display: none;
    }
    """

    BINDINGS = [
        Binding("up,left,k", "focus_prev", show=False),
        Binding("down,right,j", "focus_next", show=False),
        Binding("enter", "select", show=False),
        Binding("escape,q", "quit", show=False),
    ]

    def __init__(
        self,
        items: list[SuggestionItem],
        query: str,
        mode: str,
        missing_tokens: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.items = items
        self.search_query = query
        self.mode = mode
        self.missing_tokens = missing_tokens
        self.copied_command: str | None = None

    def compose(self) -> ComposeResult:
        yield Label(f"[bold #58a6ff]shix[/]  [italic #484f58]{self.mode}[/]", id="title-text")
        yield Label(f"[#58a6ff]>[/] [bold #e6edf3]{self.search_query}[/]", id="query-text")

        warning = Label("", id="warning")
        if self.missing_tokens:
            warning.update(f"[#d29922]no history for: {', '.join(self.missing_tokens)}[/]")
            warning.add_class("visible")
        yield warning

        if self.items:
            yield Label(f"[#484f58]{len(self.items)} results[/]", id="pills-label")
            with PillsContainer(id="pills-area"):
                for i, item in enumerate(self.items, 1):
                    with ResultRow():
                        yield Label(f"[#484f58]{i:>3}[/]", classes="pill-index")
                        yield CommandPill(item.command)
        else:
            yield Label("[#d29922]No matches found. Try different keywords.[/]")

        yield Label("[#58a6ff]arrows[/] [#484f58]navigate[/]  [#58a6ff]enter/click[/] [#484f58]copy[/]  [#58a6ff]esc[/] [#484f58]quit[/]", id="status-bar")

    def on_mount(self) -> None:
        pills = self.query(CommandPill)
        if pills:
            pills[0].focus()

    def action_focus_next(self) -> None:
        pills = self.query(CommandPill)
        if not pills:
            return
        focused = self.screen.focused
        current = -1
        for i, p in enumerate(pills):
            if p is focused:
                current = i
                break
        nxt = current + 1 if current < len(pills) - 1 else 0
        pills[nxt].focus(scroll_visible=False)
        pills[nxt].scroll_visible(animate=False)

    def action_focus_prev(self) -> None:
        pills = self.query(CommandPill)
        if not pills:
            return
        focused = self.screen.focused
        current = -1
        for i, p in enumerate(pills):
            if p is focused:
                current = i
                break
        prev = current - 1 if current > 0 else len(pills) - 1
        pills[prev].focus(scroll_visible=False)
        pills[prev].scroll_visible(animate=False)

    def action_select(self) -> None:
        focused = self.screen.focused
        if isinstance(focused, CommandPill):
            self._copy_command(focused.command)

    def on_command_pill_selected(self, message: CommandPill.Selected) -> None:
        self._copy_command(message.command)

    def _copy_command(self, command: str) -> None:
        self.copied_command = command
        self.clipboard_ok = False
        try:
            import os, platform, pyperclip
            # On macOS/Windows clipboard is always available
            # On Linux, only try if a display server is present
            if platform.system() == "Linux" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                raise RuntimeError("No display")
            pyperclip.copy(command)
            self.clipboard_ok = True
        except Exception:
            self.clipboard_ok = False

        status = self.query_one("#status-bar", Label)
        status.update(f"[bold #ffffff]Copied:[/] {command}")
        status.add_class("copied")
        self.set_timer(0.4, self._exit_after_copy)

    def _exit_after_copy(self) -> None:
        self.exit(self.copied_command)


def run_tui(
    items: list[SuggestionItem],
    query: str,
    mode: str,
    missing_tokens: list[str] | None = None,
) -> tuple[str | None, bool]:
    """Run the TUI and return (command, clipboard_ok)."""
    app = ShixApp(items, query, mode, missing_tokens)
    result = app.run()
    return result, getattr(app, "clipboard_ok", False)
