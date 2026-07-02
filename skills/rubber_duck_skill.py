"""
skills/rubber_duck_skill.py — Rubber duck debugging skill
"""

from __future__ import annotations

from typing import Any


def rubber_duck_handler(topic: str, user_input: str, **kwargs: Any) -> str:
    """Prompt the student to explain their code out loud (rubber duck method)."""
    return (
        "🦆 **Rubber Duck Debugging Time!**\n\n"
        "I'm going to be your rubber duck. Sometimes, just *explaining* your problem out loud "
        "reveals the solution!\n\n"
        "Please walk me through your code or thinking, **line by line**:\n\n"
        "1. What are you *trying* to make the code do?\n"
        "2. What is the code *actually* doing (as far as you can tell)?\n"
        "3. At which point does it stop doing what you expected?\n\n"
        "Take your time — explain it as if I'm a 5-year-old who knows nothing about Python. "
        "I'm listening! 🎧"
    )
