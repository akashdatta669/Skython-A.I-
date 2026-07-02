"""
mcp/tools.py — MCP tool definitions and execution logic
"""

from __future__ import annotations

from typing import Any

# ──────────────────────── Tool schemas ───────────────────────────────────────

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_student_mastery",
        "description": "Returns the mastery level and score for a specific student on a specific topic.",
        "parameters": {
            "student_id": {"type": "string", "description": "The student's UUID"},
            "topic_id": {"type": "string", "description": "The topic ID (e.g. 'variables', 'loops')"},
        },
        "required": ["student_id", "topic_id"],
    },
    {
        "name": "execute_python_code",
        "description": "Executes Python code in the secure Skython sandbox and returns stdout/stderr.",
        "parameters": {
            "code": {"type": "string", "description": "The Python code to execute"},
            "timeout_seconds": {"type": "integer", "description": "Execution timeout in seconds", "default": 10},
        },
        "required": ["code"],
    },
    {
        "name": "get_next_topic",
        "description": "Returns the next recommended topic for a student based on their curriculum state.",
        "parameters": {
            "student_id": {"type": "string", "description": "The student's UUID"},
        },
        "required": ["student_id"],
    },
    {
        "name": "analyze_code",
        "description": "Runs AST-based static analysis on Python code and returns errors, warnings, and patterns.",
        "parameters": {
            "code": {"type": "string", "description": "The Python code to analyze"},
        },
        "required": ["code"],
    },
    {
        "name": "get_hint",
        "description": "Returns the next progressive hint for the student's current challenge.",
        "parameters": {
            "session_id": {"type": "string", "description": "The session UUID"},
            "current_hint_level": {"type": "integer", "description": "Current hint level (0-2)"},
        },
        "required": ["session_id", "current_hint_level"],
    },
]


# ──────────────────────── Tool executor ──────────────────────────────────────

class MCPToolExecutor:
    """Executes MCP tools by routing to the appropriate Skython subsystem."""

    def __init__(
        self,
        memory_manager: Any,
        curriculum_engine: Any,
        sandbox_execute: Any,
        analyze_code: Any,
        teaching_engine: Any,
    ) -> None:
        self._memory = memory_manager
        self._curriculum = curriculum_engine
        self._sandbox = sandbox_execute
        self._analyze = analyze_code
        self._teaching = teaching_engine

    def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Route and execute an MCP tool call."""
        handlers = {
            "get_student_mastery": self._get_student_mastery,
            "execute_python_code": self._execute_python_code,
            "get_next_topic": self._get_next_topic,
            "analyze_code": self._analyze_code,
            "get_hint": self._get_hint,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}", "success": False}

        try:
            return handler(params)
        except Exception as exc:
            return {"error": str(exc), "success": False}

    def _get_student_mastery(self, params: dict[str, Any]) -> dict[str, Any]:
        student_id = params["student_id"]
        topic_id = params["topic_id"]
        record = self._memory.get_mastery(student_id, topic_id)
        if record:
            return {
                "success": True,
                "topic_id": record.topic_id,
                "mastery_level": record.mastery_level,
                "score": round(record.score, 3),
                "successful_exercises": record.successful_exercises,
                "failed_exercises": record.failed_exercises,
            }
        return {
            "success": True,
            "topic_id": topic_id,
            "mastery_level": "novice",
            "score": 0.0,
            "message": "No mastery record found — student has not attempted this topic yet.",
        }

    def _execute_python_code(self, params: dict[str, Any]) -> dict[str, Any]:
        code = params["code"]
        timeout = params.get("timeout_seconds", 10)
        result = self._sandbox(code, timeout=timeout)
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "execution_time": round(result.execution_time, 3),
            "error_type": result.error_type,
            "error_message": result.error_message,
        }

    def _get_next_topic(self, params: dict[str, Any]) -> dict[str, Any]:
        student_id = params["student_id"]
        next_topic = self._curriculum.get_next_topic(student_id)
        return {
            "success": True,
            "next_topic": next_topic,
            "message": f"Recommended next topic: {next_topic}" if next_topic else "All available topics mastered!",
        }

    def _analyze_code(self, params: dict[str, Any]) -> dict[str, Any]:
        code = params["code"]
        result = self._analyze(code)
        return {
            "success": True,
            "is_valid_syntax": result.is_valid_syntax,
            "parse_error": result.parse_error,
            "errors": [
                {"code": e.code, "message": e.message, "line": e.line, "suggestion": e.teaching_suggestion}
                for e in result.errors
            ],
            "warnings": [
                {"code": w.code, "message": w.message, "line": w.line, "suggestion": w.teaching_suggestion}
                for w in result.warnings
            ],
            "patterns": result.patterns,
            "summary": result.summary(),
        }

    def _get_hint(self, params: dict[str, Any]) -> dict[str, Any]:
        session_id = params["session_id"]
        current_level = params["current_hint_level"]
        session = self._memory.get_session(session_id)
        topic = session.active_topic if session else "general"
        new_level, hint_text = self._teaching.escalate_hint(
            current_level, "the current exercise", topic or "general"
        )
        return {
            "success": True,
            "new_hint_level": new_level,
            "hint_text": hint_text,
        }
