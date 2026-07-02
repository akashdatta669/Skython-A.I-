"""
engines/code_analysis.py — AST-based static code analysis
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class CodeIssue:
    code: str
    message: str
    line: int = 0
    severity: str = "warning"  # "error" | "warning" | "info"
    teaching_suggestion: str = ""


@dataclass
class CodeAnalysisResult:
    errors: list[CodeIssue] = field(default_factory=list)
    warnings: list[CodeIssue] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    parse_error: str = ""
    is_valid_syntax: bool = True

    @property
    def has_issues(self) -> bool:
        return bool(self.errors or self.warnings)

    def summary(self) -> str:
        parts: list[str] = []
        if not self.is_valid_syntax:
            parts.append(f"Syntax Error: {self.parse_error}")
        for e in self.errors:
            parts.append(f"[{e.code}] Line {e.line}: {e.message}")
        for w in self.warnings:
            parts.append(f"[{w.code}] Line {w.line}: {w.message}")
        return "; ".join(parts) if parts else "No issues found."


# ─────────────────────── Pattern visitors ────────────────────────────────────

class _CodeAnalysisVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: list[str]) -> None:
        self._lines = source_lines
        self.issues: list[CodeIssue] = []
        self._assigned_names: set[str] = set()
        self._loop_targets: list[set[str]] = []  # stack of loop target names

    def _line(self, node: ast.AST) -> int:
        return getattr(node, "lineno", 0)

    # ── L-002: Assignment inside `if` condition ──────────────────────────────
    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        if isinstance(node.test, ast.NamedExpr):
            pass  # walrus operator := is intentional
        elif isinstance(node.test, (ast.Assign,)):
            self.issues.append(
                CodeIssue(
                    code="L-002",
                    message="Assignment '=' used inside an if-condition; did you mean '=='?",
                    line=self._line(node),
                    severity="error",
                    teaching_suggestion="Compare values with '==' not '='. Assignment happens, but the condition is always True.",
                )
            )
        # Also detect patterns like `if x = y:` which is a SyntaxError in Python 3
        self.generic_visit(node)

    # ── L-003: while True with no break ─────────────────────────────────────
    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        is_infinite = (
            isinstance(node.test, ast.Constant) and node.test.value is True
        ) or (
            isinstance(node.test, ast.NameConstant) and node.test.value is True  # type: ignore[attr-defined]
        )
        if is_infinite:
            # Check for any Break inside this while (at any depth)
            has_break = any(
                isinstance(child, ast.Break)
                for child in ast.walk(node)
            )
            if not has_break:
                self.issues.append(
                    CodeIssue(
                        code="L-003",
                        message="'while True' loop detected with no 'break' statement — potential infinite loop.",
                        line=self._line(node),
                        severity="warning",
                        teaching_suggestion="Every 'while True' loop needs a 'break' condition to exit.",
                    )
                )
        self.generic_visit(node)

    # ── L-006: Modifying list while iterating over it ────────────────────────
    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        # Collect the iterable name
        iter_name: str | None = None
        if isinstance(node.iter, ast.Name):
            iter_name = node.iter.id

        if iter_name:
            for child in ast.walk(node):
                if isinstance(child, (ast.Call,)):
                    # Look for iter_name.append / iter_name.remove / iter_name.pop
                    if (
                        isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Name)
                        and child.func.value.id == iter_name
                        and child.func.attr in ("append", "remove", "pop", "insert", "extend")
                    ):
                        self.issues.append(
                            CodeIssue(
                                code="L-006",
                                message=f"Modifying list '{iter_name}' while iterating over it can cause unexpected behavior.",
                                line=self._line(child),
                                severity="error",
                                teaching_suggestion="Iterate over a copy: 'for x in my_list[:]' or collect changes and apply after the loop.",
                            )
                        )
        self.generic_visit(node)

    # ── R-001: Use before assignment ─────────────────────────────────────────
    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._assigned_names.add(target.id)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if (
            isinstance(node.ctx, ast.Load)
            and node.id not in self._assigned_names
            and not node.id.startswith("_")
            and node.id
            not in dir(__builtins__ if isinstance(__builtins__, dict) else type(__builtins__))
            and node.id not in ("True", "False", "None", "print", "range", "len",
                                 "int", "str", "float", "list", "dict", "set",
                                 "tuple", "type", "isinstance", "enumerate",
                                 "zip", "map", "filter", "sorted", "reversed",
                                 "input", "open", "sum", "min", "max", "abs",
                                 "round", "chr", "ord", "hex", "bin", "oct",
                                 "Exception", "ValueError", "TypeError", "KeyError",
                                 "IndexError", "NameError", "StopIteration",
                                 "self", "cls", "args", "kwargs")
        ):
            # Heuristic only — not flagging to avoid false positives in complex code
            pass
        self.generic_visit(node)


# ─────────────────────────── Public API ──────────────────────────────────────

def analyze(code_string: str) -> CodeAnalysisResult:
    """
    Analyze Python code for common errors and teaching opportunities.
    Returns a CodeAnalysisResult with errors, warnings, and patterns.
    """
    result = CodeAnalysisResult()

    if not code_string.strip():
        return result

    # Step 1: Parse
    try:
        tree = ast.parse(code_string)
        result.is_valid_syntax = True
    except SyntaxError as exc:
        result.is_valid_syntax = False
        result.parse_error = f"{exc.msg} (line {exc.lineno})"
        result.errors.append(
            CodeIssue(
                code="S-001",
                message=f"SyntaxError: {exc.msg}",
                line=exc.lineno or 0,
                severity="error",
                teaching_suggestion="Python requires exact syntax. Check colons (:) after if/for/while/def/class, matching parentheses, and correct indentation.",
            )
        )
        return result

    # Step 2: Walk
    source_lines = code_string.splitlines()
    visitor = _CodeAnalysisVisitor(source_lines)
    visitor.visit(tree)

    for issue in visitor.issues:
        if issue.severity == "error":
            result.errors.append(issue)
        else:
            result.warnings.append(issue)

    # Step 3: Pattern detection
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.patterns.append(f"function_definition:{node.name}")
        elif isinstance(node, ast.ClassDef):
            result.patterns.append(f"class_definition:{node.name}")
        elif isinstance(node, ast.For):
            result.patterns.append("for_loop")
        elif isinstance(node, ast.While):
            result.patterns.append("while_loop")
        elif isinstance(node, ast.Try):
            result.patterns.append("try_except")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result.patterns.append(f"import:{alias.name}")

    log.debug(
        "Code analysis: %d errors, %d warnings, %d patterns",
        len(result.errors),
        len(result.warnings),
        len(result.patterns),
    )
    return result
