"""
api/websocket.py — WebSocket endpoint for real-time LLM streaming
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)

_mentor_engine: Any = None
_memory_manager: Any = None


def init_websocket(mentor_engine: Any, memory_manager: Any) -> None:
    global _mentor_engine, _memory_manager
    _mentor_engine = mentor_engine
    _memory_manager = memory_manager


async def websocket_chat_handler(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for streaming mentor responses.
    Protocol:
      Client → {"student_name": str, "session_id": str|null, "message": str}
      Server → {"token": str} (repeated)
      Server → {"done": true, "session_id": str, "student_id": str}
    """
    await websocket.accept()
    log.info("WebSocket connection established")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"error": "Invalid JSON payload"})
                )
                continue

            student_name = data.get("student_name", "Student")
            session_id = data.get("session_id")
            message = data.get("message", "")

            if not message.strip():
                continue

            # Get or create student + session
            student = _memory_manager.get_or_create_student(student_name)
            if session_id:
                session = _memory_manager.get_session(session_id)
                if not session:
                    session = _memory_manager.create_session(student.id)
            else:
                session = _memory_manager.create_session(student.id)

            # Stream response token by token
            try:
                for token in _mentor_engine.stream_response(
                    student_id=student.id,
                    session_id=session.id,
                    user_input=message,
                ):
                    await websocket.send_text(json.dumps({"token": token}))

                await websocket.send_text(
                    json.dumps({
                        "done": True,
                        "session_id": session.id,
                        "student_id": student.id,
                    })
                )
            except Exception as exc:
                log.error("Streaming error: %s", exc)
                await websocket.send_text(
                    json.dumps({"error": str(exc), "done": True})
                )

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected")
    except Exception as exc:
        log.error("WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
