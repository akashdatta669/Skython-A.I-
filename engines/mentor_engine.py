"""
engines/mentor_engine.py — Main orchestrator for all Skython interactions
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Generator

from engines.code_analysis import analyze
from engines.curriculum_engine import CurriculumEngine
from engines.memory_manager import MemoryManager
from engines.sandbox import execute_code
from engines.teaching_engine import TeachingEngine
from llm.interface import LLMInterface
from llm.prompts import MENTOR_SYSTEM_PROMPT, STATUS_PROMPT_TEMPLATE
from security.sanitizer import sanitize

log = logging.getLogger(__name__)

# ─────────────────────── Input classification helpers ────────────────────────

_CODE_INDICATORS = re.compile(
    r"\b(def |class |for |while |if |import |print\(|=\s*[A-Za-z0-9\"'\[\{]|:\s*$)",
    re.MULTILINE,
)
_SLASH_COMMANDS = {"/hint", "/status", "/topic", "/skip", "/exit", "/help"}


@dataclass
class MentorResponse:
    content: str
    response_type: str = "chat"   # chat | hint | status | topic | error
    strategy_used: str = "general"
    hint_level: int = 0
    current_topic: str = ""
    next_topic: str | None = None
    code_result: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class MentorEngine:
    """Orchestrates all Skython subsystems into a unified mentor pipeline."""

    def __init__(
        self,
        llm: LLMInterface,
        memory: MemoryManager,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._teaching = TeachingEngine(llm)
        self._curriculum = CurriculumEngine(memory)
        self._ready = False
        self._init()

    def _init(self) -> None:
        try:
            _ = self._llm.is_available()   # warm up connection
            self._ready = True
            log.info("MentorEngine initialized successfully")
        except Exception as exc:
            log.warning("MentorEngine init warning: %s", exc)
            self._ready = True  # Still usable even if LLM is offline

    def is_ready(self) -> bool:
        return self._ready

    # ────────────────────────── Input classification ──────────────────────────

    def _classify_input(self, text: str) -> str:
        """Classify input as 'command', 'code', or 'question'."""
        stripped = text.strip()

        if stripped.startswith("/") and stripped.split()[0] in _SLASH_COMMANDS:
            return "command"

        # Code heuristic: multiple code indicators or contains newlines with indentation
        code_matches = len(_CODE_INDICATORS.findall(stripped))
        has_newline_indent = "\n    " in stripped or "\n\t" in stripped

        if code_matches >= 2 or has_newline_indent:
            return "code"

        return "question"

    # ────────────────────────── Main process_input ────────────────────────────

    def process_input(
        self,
        student_id: str,
        session_id: str,
        user_input: str,
        input_type: str = "auto",
    ) -> MentorResponse:
        """Route input through the correct pipeline and return a MentorResponse."""

        # Sanitize
        clean_input = sanitize(user_input)

        # Classify
        if input_type == "auto":
            input_type = self._classify_input(clean_input)

        # Get session state
        session = self._memory.get_session(session_id)
        current_topic = session.active_topic or "variables" if session else "variables"
        hint_level = session.hint_level if session else 0

        # Get mastery
        mastery = self._memory.get_mastery(student_id, current_topic)
        mastery_score = mastery.score if mastery else 0.0
        mastery_level = mastery.mastery_level if mastery else "novice"

        # Get recent context
        history = self._memory.get_context(session_id, n=20)
        context_str = self._build_context_string(history)

        # ── Route ────────────────────────────────────────────────────────────
        if input_type == "command":
            response = self._handle_command(
                clean_input, student_id, session_id, current_topic, hint_level, context_str
            )
        elif input_type == "code":
            response = self._handle_code(
                clean_input, student_id, session_id, current_topic,
                mastery_score, mastery_level, history, hint_level
            )
        else:
            response = self._handle_question(
                clean_input, student_id, session_id, current_topic,
                mastery_score, mastery_level, history
            )

        # ── Persist ──────────────────────────────────────────────────────────
        self._memory.save_message(
            session_id, "student", clean_input, current_topic, input_type
        )
        self._memory.save_message(
            session_id, "mentor", response.content, current_topic, response.response_type
        )

        # Update session strategy
        if session_id:
            self._memory.update_session(
                session_id,
                current_strategy=response.strategy_used,
                hint_level=response.hint_level,
            )

        response.current_topic = current_topic
        return response

    # ────────────────────────── Command handler ───────────────────────────────

    def _handle_command(
        self,
        cmd: str,
        student_id: str,
        session_id: str,
        current_topic: str,
        hint_level: int,
        context: str,
    ) -> MentorResponse:
        parts = cmd.strip().split()
        command = parts[0].lower()

        if command == "/hint":
            session = self._memory.get_session(session_id)
            hl = session.hint_level if session else 0
            new_level, hint_text = self._teaching.escalate_hint(
                hl, context or "the current exercise", current_topic, context
            )
            self._memory.update_session(session_id, hint_level=new_level)
            return MentorResponse(
                content=hint_text,
                response_type="hint",
                hint_level=new_level,
                strategy_used="hints",
            )

        elif command == "/status":
            summary = self._memory.get_student_summary(student_id)
            mastery_list = summary.get("mastery", [])
            mastery_str = ", ".join(
                f"{m['topic_id']}:{m['mastery_level']}" for m in mastery_list
            ) or "No topics attempted yet"
            student_info = summary.get("student", {})
            prompt = STATUS_PROMPT_TEMPLATE.format(
                name=student_info.get("name", "Student"),
                level=student_info.get("experience_level", "novice"),
                topics_attempted=len(mastery_list),
                mastery_scores=mastery_str,
                recent_session=current_topic,
            )
            content = self._llm.generate(prompt, system_prompt=MENTOR_SYSTEM_PROMPT)
            return MentorResponse(content=content, response_type="status")

        elif command == "/topic":
            next_topic = self._curriculum.get_next_topic(student_id)
            mastery_map = self._curriculum.get_mastery_map(student_id)
            unlocked = [t for t, info in mastery_map.items() if not info["locked"]]
            msg = (
                f"📚 **Current topic:** `{current_topic}`\n\n"
                f"⭐ **Recommended next:** `{next_topic or 'All unlocked topics mastered!'}`\n\n"
                f"🔓 **Unlocked topics:** {', '.join(f'`{t}`' for t in unlocked)}"
            )
            return MentorResponse(
                content=msg,
                response_type="topic",
                next_topic=next_topic,
            )

        elif command == "/skip":
            next_topic = self._curriculum.get_next_topic(student_id)
            if next_topic:
                self._memory.update_session(session_id, active_topic=next_topic, hint_level=0)
                return MentorResponse(
                    content=f"⏭️ Skipping to **{next_topic}**. Let's dive in! What do you already know about `{next_topic}`?",
                    response_type="topic",
                    next_topic=next_topic,
                )
            return MentorResponse(content="✅ You've completed all available topics! Try `/status` to review your progress.", response_type="chat")

        elif command == "/exit":
            self._memory.end_session(session_id)
            return MentorResponse(
                content="👋 Session saved! Your progress has been recorded. See you next time! Run `python main.py` to return.",
                response_type="chat",
            )

        elif command == "/help":
            return MentorResponse(
                content=(
                    "**Available commands:**\n\n"
                    "- `/hint` — Request a progressive hint (up to 3 levels)\n"
                    "- `/status` — View your learning progress summary\n"
                    "- `/topic` — See current and recommended next topics\n"
                    "- `/skip` — Skip to the next recommended topic\n"
                    "- `/exit` — Save session and exit\n"
                    "- `/help` — Show this help message\n\n"
                    "Or just **type naturally** — I'll figure out whether you're asking a question or sharing code! 🐍"
                ),
                response_type="chat",
            )

        return MentorResponse(
            content=f"Unknown command: `{command}`. Try `/help` for available commands.",
            response_type="error",
        )

    # ────────────────────────── Code handler ──────────────────────────────────

    def _handle_code(
        self,
        code: str,
        student_id: str,
        session_id: str,
        current_topic: str,
        mastery_score: float,
        mastery_level: str,
        history: list[dict],
        hint_level: int,
    ) -> MentorResponse:
        # 1. Static analysis
        analysis = analyze(code)
        findings = analysis.summary()

        # 2. Execute in sandbox
        exec_result = execute_code(code)

        # 3. Choose strategy
        has_error = not exec_result.success or analysis.has_issues
        strategy = self._teaching.select_strategy(
            current_topic, mastery_score, history, has_code=True, has_error=has_error
        )

        # 4. Generate mentor response
        content = self._teaching.execute_strategy(
            strategy=strategy,
            user_input=code,
            topic=current_topic,
            mastery_score=mastery_score,
            mastery_level=mastery_level,
            code=code,
            analysis_findings=findings,
        )

        # 5. Update mastery based on execution success
        self._memory.update_mastery(student_id, current_topic, exec_result.success)

        return MentorResponse(
            content=content,
            response_type="code",
            strategy_used=strategy,
            hint_level=hint_level,
            code_result={
                "success": exec_result.success,
                "stdout": exec_result.stdout,
                "stderr": exec_result.stderr,
                "execution_time": exec_result.execution_time,
                "error_type": exec_result.error_type,
                "analysis": findings,
            },
        )

    # ────────────────────────── Question handler ──────────────────────────────

    def _handle_question(
        self,
        question: str,
        student_id: str,
        session_id: str,
        current_topic: str,
        mastery_score: float,
        mastery_level: str,
        history: list[dict],
    ) -> MentorResponse:
        strategy = self._teaching.select_strategy(
            current_topic, mastery_score, history, has_code=False, has_error=False
        )
        content = self._teaching.execute_strategy(
            strategy=strategy,
            user_input=question,
            topic=current_topic,
            mastery_score=mastery_score,
            mastery_level=mastery_level,
        )
        return MentorResponse(
            content=content,
            response_type="chat",
            strategy_used=strategy,
        )

    # ────────────────────────── Streaming ─────────────────────────────────────

    def stream_response(
        self,
        student_id: str,
        session_id: str,
        user_input: str,
    ) -> Generator[str, None, None]:
        """Streaming version of process_input — yields tokens for UI streaming."""
        clean_input = sanitize(user_input)
        input_type = self._classify_input(clean_input)

        session = self._memory.get_session(session_id)
        current_topic = session.active_topic or "variables" if session else "variables"
        hint_level = session.hint_level if session else 0

        mastery = self._memory.get_mastery(student_id, current_topic)
        mastery_score = mastery.score if mastery else 0.0
        mastery_level = mastery.mastery_level if mastery else "novice"
        history = self._memory.get_context(session_id, n=20)

        if input_type == "command" and clean_input.strip().startswith("/hint"):
            new_level, _ = self._teaching.escalate_hint(
                hint_level, clean_input, current_topic
            )
            self._memory.update_session(session_id, hint_level=new_level)
            yield from self._teaching.stream_hint(hint_level, clean_input, current_topic)
            return

        strategy = self._teaching.select_strategy(
            current_topic, mastery_score, history,
            has_code=(input_type == "code"), has_error=False
        )

        full_response = []
        for token in self._teaching.stream_strategy(
            strategy=strategy,
            user_input=clean_input,
            topic=current_topic,
            mastery_score=mastery_score,
            mastery_level=mastery_level,
            code=clean_input if input_type == "code" else "",
        ):
            full_response.append(token)
            yield token

        # Persist after streaming completes
        self._memory.save_message(session_id, "student", clean_input, current_topic, input_type)
        self._memory.save_message(session_id, "mentor", "".join(full_response), current_topic, "chat")

    # ────────────────────────── Helpers ───────────────────────────────────────

    def _build_context_string(self, history: list[dict]) -> str:
        """Build a compact context string from message history."""
        lines: list[str] = []
        for msg in history[-10:]:
            role = "Student" if msg["role"] == "student" else "Skython"
            lines.append(f"{role}: {msg['content'][:200]}")
        return "\n".join(lines)

    def set_topic(self, session_id: str, topic_id: str) -> None:
        """Explicitly set the active topic for a session."""
        self._memory.update_session(session_id, active_topic=topic_id, hint_level=0)
        log.info("Session %s topic set to: %s", session_id, topic_id)
