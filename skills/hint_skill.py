"""
skills/hint_skill.py — Progressive 3-tier hint skill
"""

from __future__ import annotations

from typing import Any

HINT_MESSAGES = {
    1: (
        "💡 **Hint Level 1 (Gentle nudge):**\n\n"
        "Think about the *concept* you're working with. "
        "What are the most important properties of `{topic}`?\n\n"
        "Re-read your code slowly. Does every part do what you *think* it does?"
    ),
    2: (
        "💡 **Hint Level 2 (Pointing in the right direction):**\n\n"
        "Let me point you toward the relevant Python documentation:\n\n"
        "For `{topic}`, pay attention to:\n"
        "- The *order* of operations\n"
        "- Whether the types match what's expected\n"
        "- Any off-by-one possibilities\n\n"
        "Can you isolate the one line that's causing trouble? Try printing variables to see their actual values."
    ),
    3: (
        "💡 **Hint Level 3 (Full reveal with explanation):**\n\n"
        "You've worked hard and asked for 3 hints — you've earned the explanation! 🎓\n\n"
        "Here's the concept you were working through with `{topic}`:\n\n"
        "**The answer:** *(The LLM will fill this in based on your specific code)*\n\n"
        "**Why this works:** Understanding the *why* is more important than the *what*. "
        "Make sure you can explain this back to me in your own words after reading it!"
    ),
}


def hint_handler(hint_level: int, topic: str, user_input: str, **kwargs: Any) -> str:
    """Return the appropriate hint for the given level."""
    level = max(1, min(3, hint_level))
    template = HINT_MESSAGES[level]
    return template.format(topic=topic, user_input=user_input)
