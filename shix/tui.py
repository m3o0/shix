"""Textual TUI app for shix — interactive command suggestion browser."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
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

    def __init__(self, index: int, command: str, **kwargs) -> None:
        display = command.split("\n")[0]
        label = f"{index} {display}"
        super().__init__(label, **kwargs)
        self.command = command
        self.index = index

    def on_enter(self, event) -> None:
        """Focus this pill when mouse hovers over it."""
        self.focus()

    def on_click(self) -> None:
        self.post_message(self.Selected(self.command))


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
        background: #1e1e2e;
        padding: 1 2;
    }

    #title-text {
        color: #89b4fa;
        height: 1;
        margin-bottom: 1;
    }

    #query-text {
        color: #cdd6f4;
        height: 1;
        margin-bottom: 1;
    }

    #warning {
        color: #f9e2af;
        height: 1;
        margin-bottom: 1;
        display: none;
    }

    #warning.visible {
        display: block;
    }

    CommandPill {
        width: auto;
        height: 1;
        max-width: 100%;
        padding: 0 1;
        margin: 0 1 1 0;
        color: #a6adc8;
        background: #313244;
    }

    CommandPill:hover {
        background: #45475a;
        color: #cdd6f4;
    }

    CommandPill:focus {
        background: #89b4fa;
        color: #1e1e2e;
        text-style: bold;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #181825;
        color: #6c7086;
        padding: 0 2;
    }

    #status-bar.copied {
        background: #a6e3a1;
        color: #1e1e2e;
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
        yield Label(f"shix  [italic #6c7086]{self.mode}[/]", id="title-text")
        yield Label(f"[#89b4fa]>[/] {self.search_query}", id="query-text")

        warning = Label("", id="warning")
        if self.missing_tokens:
            warning.update(f"no history for: {', '.join(self.missing_tokens)}")
            warning.add_class("visible")
        yield warning

        if self.items:
            with PillsContainer(id="pills-area"):
                for i, item in enumerate(self.items, 1):
                    yield CommandPill(i, item.command)
        else:
            yield Label("[#f9e2af]No matches found. Try different keywords.[/]")

        yield Label("[#6c7086]arrows[/] navigate  [#6c7086]enter/click[/] copy  [#6c7086]esc[/] quit", id="status-bar")

    def on_mount(self) -> None:
        pills = self.query(CommandPill)
        if pills:
            pills[0].focus()

    def action_focus_next(self) -> None:
        pills = self.query(CommandPill)
        if not pills:
            return
        focused = self.screen.focused
        # Find current index
        current = -1
        for i, p in enumerate(pills):
            if p is focused:
                current = i
                break
        nxt = current + 1 if current < len(pills) - 1 else 0
        pills[nxt].focus()
        pills[nxt].scroll_visible()

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
        pills[prev].focus()
        pills[prev].scroll_visible()

    def action_select(self) -> None:
        focused = self.screen.focused
        if isinstance(focused, CommandPill):
            self._copy_command(focused.command)

    def on_command_pill_selected(self, message: CommandPill.Selected) -> None:
        self._copy_command(message.command)

    def _copy_command(self, command: str) -> None:
        self.copied_command = command
        try:
            import pyperclip
            pyperclip.copy(command)
        except Exception:
            pass

        status = self.query_one("#status-bar", Label)
        status.update(f"Copied: {command}")
        status.add_class("copied")
        self.set_timer(0.4, self._exit_after_copy)

    def _exit_after_copy(self) -> None:
        self.exit(self.copied_command)


def run_tui(
    items: list[SuggestionItem],
    query: str,
    mode: str,
    missing_tokens: list[str] | None = None,
) -> str | None:
    """Run the TUI and return the copied command (or None)."""
    app = ShixApp(items, query, mode, missing_tokens)
    return app.run()
