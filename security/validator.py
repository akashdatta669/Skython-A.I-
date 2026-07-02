"""
security/validator.py — AST-based pre-execution security validation
"""

from __future__ import annotations

import ast
import logging
from typing import Any

from config import BLOCKED_BUILTINS, BLOCKED_MODULES

log = logging.getLogger(__name__)


class SecurityViolation(Exception):
    """Raised when code fails the security scan."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("; ".join(violations))


class _SecurityVisitor(ast.NodeVisitor):
    """Walk an AST and collect security violations."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    # ── Import statements ────────────────────────────────────────────────────
    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base in BLOCKED_MODULES:
                self.violations.append(
                    f"SecurityViolation: import of '{alias.name}' is not permitted"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module:
            base = node.module.split(".")[0]
            if base in BLOCKED_MODULES:
                self.violations.append(
                    f"SecurityViolation: 'from {node.module} import ...' is not permitted"
                )
        self.generic_visit(node)

    # ── Blocked built-ins ────────────────────────────────────────────────────
    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func_name: str | None = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name and func_name in BLOCKED_BUILTINS:
            self.violations.append(
                f"SecurityViolation: call to '{func_name}()' is not permitted"
            )
        self.generic_visit(node)

    # ── Dunder attribute access ──────────────────────────────────────────────
    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        if node.attr.startswith("__") and node.attr.endswith("__"):
            dangerous = {
                "__class__", "__base__", "__subclasses__", "__globals__",
                "__builtins__", "__import__", "__code__", "__dict__",
                "__mro__", "__loader__", "__spec__",
            }
            if node.attr in dangerous:
                self.violations.append(
                    f"SecurityViolation: access to '{node.attr}' is not permitted"
                )
        self.generic_visit(node)

    # ── exec / eval as expressions ────────────────────────────────────────────
    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if node.id in BLOCKED_BUILTINS and isinstance(node.ctx, ast.Load):
            # Only flag if it's not inside a call (already caught by visit_Call)
            pass
        self.generic_visit(node)


def validate_code(code: str) -> tuple[bool, list[str]]:
    """
    Parse code with ast and walk for security violations.

    Returns:
        (is_safe, violations_list)
    """
    violations: list[str] = []

    # Step 1: parse
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        # Syntax errors are not security violations — report separately
        return True, []  # Let sandbox handle syntax errors at runtime

    # Step 2: walk
    visitor = _SecurityVisitor()
    visitor.visit(tree)
    violations.extend(visitor.violations)

    if violations:
        log.warning("Code security scan failed: %s", violations)

    return len(violations) == 0, violations
