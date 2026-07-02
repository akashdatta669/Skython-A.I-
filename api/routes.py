"""
api/routes.py — FastAPI REST endpoints for Skython AI
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# These will be injected at startup
_mentor_engine: Any = None
_memory_manager: Any = None
_curriculum_engine: Any = None


def init_routes(mentor_engine: Any, memory_manager: Any, curriculum_engine: Any) -> None:
    global _mentor_engine, _memory_manager, _curriculum_engine
    _mentor_engine = mentor_engine
    _memory_manager = memory_manager
    _curriculum_engine = curriculum_engine


# ─────────────────────────── Request/Response Models ──────────────────────────

class ChatRequest(BaseModel):
    student_name: str
    session_id: str | None = None
    message: str
    input_type: str = "auto"


class ChatResponse(BaseModel):
    content: str
    session_id: str
    student_id: str
    response_type: str
    strategy_used: str
    hint_level: int
    current_topic: str


class StudentRequest(BaseModel):
    name: str


class ExecuteCodeRequest(BaseModel):
    code: str
    timeout: int = 10


class SetTopicRequest(BaseModel):
    session_id: str
    topic_id: str


# ─────────────────────────── Endpoints ────────────────────────────────────────

@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    db_ok = True
    try:
        from database.db import health_check as db_health
        db_ok = db_health()
    except Exception:
        db_ok = False

    llm_ok = False
    try:
        llm_ok = _mentor_engine._llm.is_available() if _mentor_engine else False
    except Exception:
        llm_ok = False

    return {
        "status": "ok",
        "database": "ok" if db_ok else "error",
        "llm": "ok" if llm_ok else "offline",
        "mentor_engine": "ready" if (_mentor_engine and _mentor_engine.is_ready()) else "not ready",
    }


@router.post("/student")
async def create_or_get_student(req: StudentRequest) -> dict[str, Any]:
    """Create or retrieve a student by name."""
    try:
        student = _memory_manager.get_or_create_student(req.name)
        return {
            "student_id": student.id,
            "name": student.name,
            "experience_level": student.experience_level,
        }
    except Exception as exc:
        log.error("Student create/get error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/session")
async def create_session(student_id: str, topic: str | None = None) -> dict[str, Any]:
    """Create a new mentor session."""
    try:
        session = _memory_manager.create_session(student_id, topic)
        return {"session_id": session.id, "student_id": student_id, "topic": topic}
    except Exception as exc:
        log.error("Session create error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    """Main chat endpoint — process a student message."""
    try:
        # Get or create student
        student = _memory_manager.get_or_create_student(req.student_name)

        # Get or create session
        if req.session_id:
            session = _memory_manager.get_session(req.session_id)
            if not session:
                session = _memory_manager.create_session(student.id)
        else:
            session = _memory_manager.create_session(student.id)

        # Process
        response = _mentor_engine.process_input(
            student_id=student.id,
            session_id=session.id,
            user_input=req.message,
            input_type=req.input_type,
        )

        return {
            "content": response.content,
            "session_id": session.id,
            "student_id": student.id,
            "response_type": response.response_type,
            "strategy_used": response.strategy_used,
            "hint_level": response.hint_level,
            "current_topic": response.current_topic,
            "code_result": response.code_result,
        }
    except Exception as exc:
        log.error("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": 500})


@router.post("/execute")
async def execute_code(req: ExecuteCodeRequest) -> dict[str, Any]:
    """Execute Python code in the sandbox."""
    try:
        from engines.sandbox import execute_code as sandbox_execute
        result = sandbox_execute(req.code, timeout=req.timeout)
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "execution_time": round(result.execution_time, 3),
            "error_type": result.error_type,
            "error_message": result.error_message,
        }
    except Exception as exc:
        log.error("Execute code error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analyze")
async def analyze_code(code: str) -> dict[str, Any]:
    """Run static analysis on Python code."""
    try:
        from engines.code_analysis import analyze
        result = analyze(code)
        return {
            "is_valid_syntax": result.is_valid_syntax,
            "parse_error": result.parse_error,
            "errors": [
                {"code": e.code, "message": e.message, "line": e.line}
                for e in result.errors
            ],
            "warnings": [
                {"code": w.code, "message": w.message, "line": w.line}
                for w in result.warnings
            ],
            "patterns": result.patterns,
            "summary": result.summary(),
        }
    except Exception as exc:
        log.error("Analyze error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/student/{student_id}/summary")
async def get_student_summary(student_id: str) -> dict[str, Any]:
    """Get full student summary with mastery and misconceptions."""
    try:
        summary = _memory_manager.get_student_summary(student_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Student not found")
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Student summary error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/student/{student_id}/curriculum")
async def get_curriculum(student_id: str) -> dict[str, Any]:
    """Get the full mastery map and next topic for a student."""
    try:
        mastery_map = _curriculum_engine.get_mastery_map(student_id)
        next_topic = _curriculum_engine.get_next_topic(student_id)
        return {"mastery_map": mastery_map, "next_topic": next_topic}
    except Exception as exc:
        log.error("Curriculum error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/session/topic")
async def set_topic(req: SetTopicRequest) -> dict[str, Any]:
    """Set the active topic for a session."""
    try:
        _mentor_engine.set_topic(req.session_id, req.topic_id)
        return {"success": True, "session_id": req.session_id, "topic": req.topic_id}
    except Exception as exc:
        log.error("Set topic error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
