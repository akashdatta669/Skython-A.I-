"""
engines/teaching_engine.py — Teaching strategy selection and hint escalation
"""

from __future__ import annotations

import logging
from typing import Any

from llm.interface import LLMInterface
from llm.prompts import (
    ANALOGY_PROMPT_TEMPLATE,
    CODE_TRACE_PROMPT_TEMPLATE,
    GENERAL_QUESTION_PROMPT_TEMPLATE,
    HINT_PROMPT_TEMPLATES,
    MENTOR_SYSTEM_PROMPT,
    RUBBER_DUCK_PROMPT_TEMPLATE,
)

log = logging.getLogger(__name__)

STRATEGIES = ["analogy_first", "code_trace", "rubber_duck", "hints", "general"]


class TeachingEngine:
    def __init__(self, llm: LLMInterface) -> None:
        self._llm = llm

    # ────────────────────────── Strategy selection ────────────────────────────

    def select_strategy(
        self,
        topic: str,
        mastery_score: float,
        history: list[dict[str, Any]],
        has_code: bool = False,
        has_error: bool = False,
    ) -> str:
        """Choose the best teaching strategy for the student's current state."""

        # Recent hint usage: if student has been asking for hints → continue hints
        recent_types = [m.get("type", "") for m in history[-5:]]
        if recent_types.count("hint") >= 2:
            return "hints"

        if has_error:
            return "rubber_duck"

        if has_code:
            return "code_trace"

        if mastery_score < 0.3:
            return "analogy_first"

        if mastery_score < 0.6:
            return "general"

        return "general"

    # ────────────────────────── Strategy execution ────────────────────────────

    def execute_strategy(
        self,
        strategy: str,
        user_input: str,
        topic: str,
        mastery_score: float,
        mastery_level: str,
        code: str = "",
        analysis_findings: str = "",
        context: str = "",
    ) -> str:
        """Build the prompt for the chosen strategy and call the LLM."""

        if strategy == "analogy_first":
            prompt = ANALOGY_PROMPT_TEMPLATE.format(
                topic=topic,
                score=mastery_score,
                user_input=user_input,
            )
        elif strategy == "code_trace":
            # Find a line number from findings if available
            line = "?"
            if analysis_findings and "Line" in analysis_findings:
                try:
                    line = analysis_findings.split("Line")[1].split(":")[0].strip()
                except Exception:
                    pass
            prompt = CODE_TRACE_PROMPT_TEMPLATE.format(
                code=code or user_input,
                analysis_findings=analysis_findings or "No specific errors found.",
                line=line,
                user_input=user_input,
            )
        elif strategy == "rubber_duck":
            prompt = RUBBER_DUCK_PROMPT_TEMPLATE.format(
                topic=topic,
                user_input=user_input,
            )
        else:
            prompt = GENERAL_QUESTION_PROMPT_TEMPLATE.format(
                topic=topic,
                mastery_level=mastery_level,
                user_input=user_input,
            )

        return self._llm.generate(prompt, system_prompt=MENTOR_SYSTEM_PROMPT)

    def stream_strategy(
        self,
        strategy: str,
        user_input: str,
        topic: str,
        mastery_score: float,
        mastery_level: str,
        code: str = "",
        analysis_findings: str = "",
        context: str = "",
    ):
        """Same as execute_strategy but yields tokens for streaming."""
        if strategy == "analogy_first":
            prompt = ANALOGY_PROMPT_TEMPLATE.format(
                topic=topic,
                score=mastery_score,
                user_input=user_input,
            )
        elif strategy == "code_trace":
            prompt = CODE_TRACE_PROMPT_TEMPLATE.format(
                code=code or user_input,
                analysis_findings=analysis_findings or "No issues found.",
                line="?",
                user_input=user_input,
            )
        elif strategy == "rubber_duck":
            prompt = RUBBER_DUCK_PROMPT_TEMPLATE.format(
                topic=topic,
                user_input=user_input,
            )
        else:
            prompt = GENERAL_QUESTION_PROMPT_TEMPLATE.format(
                topic=topic,
                mastery_level=mastery_level,
                user_input=user_input,
            )

        yield from self._llm.stream(prompt, system_prompt=MENTOR_SYSTEM_PROMPT)

    # ────────────────────────── Hint escalation ───────────────────────────────

    def escalate_hint(
        self,
        current_level: int,
        user_input: str,
        topic: str,
        context: str = "",
    ) -> tuple[int, str]:
        """
        Increment hint level (1→2→3) and return (new_level, hint_response).
        At level 3: always provides the full answer with explanation.
        """
        new_level = min(current_level + 1, 3)
        template = HINT_PROMPT_TEMPLATES[new_level]
        prompt = template.format(
            topic=topic,
            user_input=user_input,
            context=context,
        )
        response = self._llm.generate(prompt, system_prompt=MENTOR_SYSTEM_PROMPT)
        log.debug("Hint escalated to level %d", new_level)
        return new_level, response

    def stream_hint(
        self,
        current_level: int,
        user_input: str,
        topic: str,
        context: str = "",
    ):
        """Streaming version of escalate_hint. Yields tokens, returns new level."""
        new_level = min(current_level + 1, 3)
        template = HINT_PROMPT_TEMPLATES[new_level]
        prompt = template.format(
            topic=topic,
            user_input=user_input,
            context=context,
        )
        yield from self._llm.stream(prompt, system_prompt=MENTOR_SYSTEM_PROMPT)
