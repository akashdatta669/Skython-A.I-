"""
skills/code_trace_skill.py — Step-by-step code tracing skill
"""

from __future__ import annotations

import ast
from typing import Any


def code_trace_handler(code: str, user_input: str, **kwargs: Any) -> str:
    """Generate a Socratic code-tracing prompt."""
    try:
        tree = ast.parse(code)
        lines = code.strip().splitlines()
        interesting_lines: list[tuple[int, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.If, ast.For, ast.While, ast.Return, ast.Call)):
                lineno = getattr(node, "lineno", None)
                if lineno and 1 <= lineno <= len(lines):
                    line_content = lines[lineno - 1].strip()
                    if (lineno, line_content) not in interesting_lines:
                        interesting_lines.append((lineno, line_content))

        interesting_lines.sort(key=lambda x: x[0])

        trace_steps = ""
        for i, (lineno, content) in enumerate(interesting_lines[:5], 1):
            trace_steps += f"  **Step {i} (Line {lineno}):** `{content}`\n"

        if not trace_steps:
            trace_steps = "  Walk through each line of your code...\n"

    except SyntaxError:
        trace_steps = "  (Fix the syntax error first, then we'll trace!)\n"

    return (
        f"Let's trace through your code together! 🔍\n\n"
        f"Here are the key steps I want you to walk me through:\n\n"
        f"{trace_steps}\n"
        f"For each step, tell me: **What value does each variable hold at that point?**\n\n"
        f"Start with Step 1. What do you think happens there?"
    )
