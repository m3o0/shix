"""Ollama integration for generating command suggestions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT = """\
You are shix, a shell command assistant. The user will describe what they want to do, \
and you will suggest shell commands.

Rules:
- Return the number of suggestions the user asks for, ranked by relevance
- Each suggestion has a "command" and a short "explanation" (one sentence)
- If the user's history contains a relevant command, suggest it first
- If no good match exists in history, suggest the correct command anyway — you are not limited to history
- Use the history to understand the user's environment (OS, tools installed, preferences)
- If the history shows usage of specific tools (e.g. docker, kubectl, git), prefer those
- Output valid JSON only, no markdown fences, no extra text

Output format (JSON array):
[
  {"command": "...", "explanation": "..."},
  ...
]
"""


@dataclass
class Suggestion:
    command: str
    explanation: str


def _build_prompt(history: list[str], query: str, count: int = 5) -> str:
    """Build the user prompt with history context and query."""
    history_block = "\n".join(history[-200:])  # trim to fit context
    return (
        f"Here are my recent shell commands for context:\n"
        f"```\n{history_block}\n```\n\n"
        f"I want to: {query}\n\n"
        f"Suggest {count} commands as a JSON array."
    )


def _parse_suggestions(text: str) -> list[Suggestion]:
    """Parse the model response into Suggestion objects."""
    # Try to find JSON array in the response
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip().rstrip("`")

    # Find the JSON array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return []

    suggestions = []
    for item in data:
        if isinstance(item, dict) and "command" in item:
            suggestions.append(
                Suggestion(
                    command=str(item["command"]),
                    explanation=str(item.get("explanation", "")),
                )
            )
    return suggestions


def get_suggestions(
    history: list[str],
    query: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    count: int = 5,
) -> list[Suggestion]:
    """Query Ollama for command suggestions.

    Raises httpx.ConnectError if Ollama is not running.
    """
    prompt = _build_prompt(history, query, count)

    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        },
        timeout=120.0,
    )
    response.raise_for_status()

    body = response.json()
    content = body.get("message", {}).get("content", "")
    return _parse_suggestions(content)
