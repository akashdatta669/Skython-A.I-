"""
security/sanitizer.py — Input sanitization and prompt injection defense
"""

from __future__ import annotations

import html
import logging
import re

from config import MAX_INPUT_LENGTH

log = logging.getLogger(__name__)

# ──────────────────────── Injection patterns ──────────────────────────────────
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(previous|prior|all)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"forget\s+(your\s+)?(persona|role|instructions?)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a\s+different)", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"override\s+(your|the)\s+(instructions?|rules?|guidelines?)", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*[:=]", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]", re.IGNORECASE),
]

_FILTER_REPLACEMENT = "[FILTERED]"


def sanitize(raw: str, escape_html: bool = False) -> str:
    """
    Clean user input:
    1. Strip whitespace
    2. Truncate to MAX_INPUT_LENGTH
    3. Replace prompt-injection patterns with [FILTERED]
    4. Optionally HTML-escape for rendering
    """
    if not isinstance(raw, str):
        raw = str(raw)

    # 1. Strip
    text = raw.strip()

    # 2. Truncate
    if len(text) > MAX_INPUT_LENGTH:
        log.warning("Input truncated from %d → %d chars", len(text), MAX_INPUT_LENGTH)
        text = text[:MAX_INPUT_LENGTH]

    # 3. Neutralize injections
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            log.warning("Prompt injection pattern detected and filtered: %s", pattern.pattern)
            text = pattern.sub(_FILTER_REPLACEMENT, text)

    # 4. HTML-escape if requested
    if escape_html:
        text = html.escape(text)

    return text


def is_safe_input(raw: str) -> tuple[bool, list[str]]:
    """
    Returns (is_safe, list_of_violations).
    Safe means no injection patterns and within length.
    """
    violations: list[str] = []

    if len(raw) > MAX_INPUT_LENGTH:
        violations.append(f"Input exceeds maximum length ({len(raw)} > {MAX_INPUT_LENGTH})")

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(raw):
            violations.append(f"Prompt injection pattern matched: {pattern.pattern}")

    return len(violations) == 0, violations
