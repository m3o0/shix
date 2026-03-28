"""Sanitize shell history by redacting secrets, tokens, and passwords."""

from __future__ import annotations

import re

REDACTED = "<REDACTED>"

# Patterns that match common secret formats in shell commands
_PATTERNS: list[re.Pattern[str]] = [
    # API keys / tokens passed as env vars or flags (KEY=value, --token=value, --token value)
    re.compile(
        r"(?i)(api[_-]?key|api[_-]?secret|token|secret|password|passwd|pwd|auth)"
        r"[\s=:]+['\"]?([A-Za-z0-9_\-./+]{8,})['\"]?"
    ),
    # Bearer tokens
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9_\-./+]{8,})"),
    # AWS-style keys (AKIA...)
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # Generic long hex/base64 strings that look like secrets (32+ chars)
    re.compile(r"(?i)(?:key|token|secret|password|credential)s?\s*[=:]\s*['\"]?([A-Za-z0-9_\-./+]{32,})['\"]?"),
    # URLs with embedded credentials (https://user:pass@host)
    re.compile(r"(https?://)([^:]+):([^@]+)@"),
    # export VAR=secret patterns
    re.compile(r"(?i)export\s+\w*(secret|token|key|password|passwd|api|auth)\w*\s*=\s*['\"]?(.+?)['\"]?\s*$"),
    # -p password or --password=xxx
    re.compile(r"(?i)(-p\s+|--password[=\s]+)['\"]?(\S+)['\"]?"),
    # SSH private key paths are fine, but inline keys are not
    re.compile(r"-----BEGIN[A-Z ]+PRIVATE KEY-----"),
    # GitHub/GitLab personal access tokens (ghp_, glpat-, etc.)
    re.compile(r"(ghp_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9\-]{20,})"),
    # npm tokens
    re.compile(r"npm_[A-Za-z0-9]{36}"),
]


def _redact_line(line: str) -> str:
    """Redact secrets from a single history line."""
    result = line

    # URL credentials: https://user:pass@host -> https://***:***@host
    result = re.sub(
        r"(https?://)([^:]+):([^@]+)@",
        rf"\1{REDACTED}:{REDACTED}@",
        result,
    )

    # -p password flag
    result = re.sub(
        r"(?i)(-p\s+|--password[=\s]+)['\"]?\S+['\"]?",
        rf"\1{REDACTED}",
        result,
    )

    # export SECRET_VAR=value
    result = re.sub(
        r"(?i)(export\s+\w*(?:secret|token|key|password|passwd|api|auth)\w*\s*=\s*)['\"]?.+?['\"]?\s*$",
        rf"\1{REDACTED}",
        result,
    )

    # KEY=value, --token=value, --token value
    result = re.sub(
        r"(?i)((?:api[_-]?key|api[_-]?secret|token|secret|password|passwd|pwd|auth)[\s=:]+)['\"]?[A-Za-z0-9_\-./+]{8,}['\"]?",
        rf"\1{REDACTED}",
        result,
    )

    # Bearer tokens
    result = re.sub(
        r"(?i)(bearer\s+)[A-Za-z0-9_\-./+]{8,}",
        rf"\1{REDACTED}",
        result,
    )

    # AWS keys
    result = re.sub(r"AKIA[0-9A-Z]{16}", REDACTED, result)

    # GitHub/GitLab tokens
    result = re.sub(r"ghp_[A-Za-z0-9]{36}", REDACTED, result)
    result = re.sub(r"glpat-[A-Za-z0-9\-]{20,}", REDACTED, result)
    result = re.sub(r"npm_[A-Za-z0-9]{36}", REDACTED, result)

    return result


def sanitize(commands: list[str]) -> list[str]:
    """Sanitize a list of shell commands by redacting secrets."""
    return [_redact_line(cmd) for cmd in commands]
