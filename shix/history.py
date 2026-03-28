"""Cross-platform shell history reader."""

from __future__ import annotations

import os
import platform
from pathlib import Path


def _get_history_paths() -> list[Path]:
    """Return candidate history file paths for the current platform."""
    home = Path.home()
    system = platform.system()

    if system == "Windows":
        # PowerShell PSReadLine history
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            ps_history = Path(appdata) / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt"
            return [ps_history]
        return []

    # macOS / Linux — prefer zsh, fall back to bash
    return [
        home / ".zsh_history",
        home / ".bash_history",
    ]


def _parse_zsh_history_line(raw: str) -> str | None:
    """Parse a single zsh history line, handling the extended format.

    Zsh extended history format: `: <timestamp>:<duration>;<command>`
    Regular format: just the command.
    Multi-line commands use trailing backslash continuation.
    """
    line = raw.strip()
    if not line:
        return None

    # Extended history format
    if line.startswith(": ") and ";" in line:
        _, _, rest = line.partition(";")
        return rest.strip() or None

    return line


def _read_file_tail(path: Path, max_lines: int = 0) -> list[str]:
    """Read lines from a file. If max_lines > 0, return only the last N lines."""
    try:
        raw = path.read_bytes()
    except (OSError, PermissionError):
        return []

    # Try utf-8 first, fall back to latin-1 (never fails)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    lines = text.splitlines()
    return lines[-max_lines:] if max_lines > 0 else lines


def read_history(max_lines: int = 0) -> list[str]:
    """Read the most recent shell commands from history.

    Tries platform-appropriate history files in priority order.
    Returns deduplicated commands preserving most-recent order.
    """
    paths = _get_history_paths()

    for path in paths:
        if not path.exists():
            continue

        raw_lines = _read_file_tail(path, max_lines * 2 if max_lines > 0 else 0)

        # Determine if this is a zsh history file
        is_zsh = "zsh" in path.name.lower()

        commands: list[str] = []
        if is_zsh:
            # Handle multi-line commands (backslash continuation)
            buffer = ""
            for raw in raw_lines:
                if buffer:
                    buffer += "\n" + raw.rstrip("\\").strip()
                    if not raw.endswith("\\"):
                        commands.append(buffer)
                        buffer = ""
                    continue

                if raw.rstrip().endswith("\\"):
                    parsed = _parse_zsh_history_line(raw.rstrip("\\"))
                    if parsed:
                        buffer = parsed
                    continue

                parsed = _parse_zsh_history_line(raw)
                if parsed:
                    commands.append(parsed)

            if buffer:
                commands.append(buffer)
        else:
            # bash / PowerShell — plain line-per-command
            for raw in raw_lines:
                line = raw.strip()
                if line:
                    commands.append(line)

        # Deduplicate keeping last occurrence (most recent)
        seen: set[str] = set()
        unique: list[str] = []
        for cmd in reversed(commands):
            if cmd not in seen:
                seen.add(cmd)
                unique.append(cmd)
        unique.reverse()

        return unique[-max_lines:] if max_lines > 0 else unique

    return []
