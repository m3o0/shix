"""Offline fuzzy search engine for shell history."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Map natural language terms to common command patterns
COMMAND_ALIASES: dict[str, list[str]] = {
    "find": ["find", "locate", "fd", "ls", "grep", "rg"],
    "delete": ["rm", "rmdir", "trash", "del"],
    "copy": ["cp", "rsync", "scp"],
    "move": ["mv"],
    "search": ["grep", "rg", "ag", "ack", "find"],
    "install": ["brew install", "apt install", "pip install", "npm install", "cargo install"],
    "process": ["ps", "top", "htop", "kill", "pkill"],
    "network": ["curl", "wget", "ping", "netstat", "ss", "nmap", "dig", "nslookup"],
    "disk": ["df", "du", "ncdu"],
    "docker": ["docker", "docker-compose", "podman"],
    "git": ["git"],
    "size": ["du", "ls -l", "wc", "stat"],
    "permission": ["chmod", "chown", "chgrp"],
    "compress": ["tar", "zip", "gzip", "bzip2", "xz", "7z"],
    "extract": ["tar", "unzip", "gunzip"],
    "edit": ["vim", "nvim", "nano", "code", "emacs"],
    "serve": ["python -m http.server", "npx serve", "nginx"],
    "port": ["lsof -i", "netstat", "ss"],
    "log": ["tail", "less", "journalctl", "cat"],
    "ssh": ["ssh", "scp", "sftp"],
    "env": ["env", "printenv", "export", "set"],
    "start": ["systemctl start", "docker start", "npm start", "brew services start"],
    "stop": ["systemctl stop", "docker stop", "kill", "pkill", "brew services stop"],
    "restart": ["systemctl restart", "docker restart", "brew services restart"],
    "list": ["ls", "ll", "exa", "tree"],
    "download": ["curl", "wget", "aria2c"],
    "upload": ["scp", "rsync", "curl -X POST"],
}


@dataclass
class FuzzyResult:
    command: str
    score: float
    reason: str


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens."""
    return re.findall(r"[a-zA-Z0-9_./-]+", text.lower())


def _score_command(command: str, query_tokens: list[str], alias_commands: set[str]) -> tuple[float, str]:
    """Score a command against the query. Returns (score, reason)."""
    cmd_lower = command.lower()
    cmd_tokens = _tokenize(command)
    score = 0.0
    reasons: list[str] = []

    # Direct token matches in command
    matched_tokens = [t for t in query_tokens if t in cmd_lower]
    if matched_tokens:
        score += len(matched_tokens) * 3.0
        reasons.append(f"matches: {', '.join(matched_tokens)}")

    # Alias matches — only match against the first token (the actual command)
    cmd_base = cmd_tokens[0] if cmd_tokens else ""
    for alias_cmd in alias_commands:
        alias_parts = alias_cmd.lower().split()
        # The command base must start with the alias, or all parts appear at the start
        if len(alias_parts) == 1 and cmd_base == alias_parts[0]:
            score += 2.0
            reasons.append(f"relates to: {alias_cmd}")
            break
        elif len(alias_parts) > 1 and cmd_lower.startswith(alias_cmd.lower()):
            score += 2.5
            reasons.append(f"relates to: {alias_cmd}")
            break

    # Partial/substring matches — only against the first few tokens (the command itself, not args/URLs)
    cmd_head_tokens = cmd_tokens[:3]
    for token in query_tokens:
        if len(token) >= 4 and token not in cmd_lower:
            for cmd_token in cmd_head_tokens:
                if token in cmd_token or cmd_token in token:
                    score += 1.0
                    break

    if score == 0:
        return 0.0, ""

    reason = "; ".join(reasons) if reasons else "partial match"
    return score, reason


def fuzzy_search(history: list[str], query: str, max_results: int = 3) -> list[FuzzyResult]:
    """Search shell history using fuzzy keyword matching.

    Matches query tokens against commands and uses alias mappings
    to connect natural language terms to shell commands.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Build set of relevant command patterns from aliases
    alias_commands: set[str] = set()
    for token in query_tokens:
        for alias_key, commands in COMMAND_ALIASES.items():
            if token in alias_key or alias_key in token:
                alias_commands.update(commands)

    # Score all history commands
    scored: list[FuzzyResult] = []
    for cmd in history:
        score, reason = _score_command(cmd, query_tokens, alias_commands)
        if score > 0:
            scored.append(FuzzyResult(command=cmd, score=score, reason=reason))

    # Sort by score descending, deduplicate
    scored.sort(key=lambda r: r.score, reverse=True)

    seen: set[str] = set()
    results: list[FuzzyResult] = []
    for r in scored:
        if r.command not in seen:
            seen.add(r.command)
            results.append(r)
            if len(results) >= max_results:
                break

    return results
