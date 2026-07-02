"""
engines/curriculum_engine.py — Topic DAG and adaptive sequencing
"""

from __future__ import annotations

import logging
from typing import Any

from engines.memory_manager import MemoryManager

log = logging.getLogger(__name__)

# ─────────────────────────── Topic DAG ───────────────────────────────────────

TOPIC_DAG: dict[str, dict[str, Any]] = {
    "variables":       {"prerequisites": [],                            "difficulty": 1},
    "data_types":      {"prerequisites": ["variables"],                 "difficulty": 1},
    "operators":       {"prerequisites": ["variables", "data_types"],   "difficulty": 2},
    "control_flow":    {"prerequisites": ["operators"],                 "difficulty": 2},
    "loops":           {"prerequisites": ["control_flow"],              "difficulty": 3},
    "functions":       {"prerequisites": ["loops"],                     "difficulty": 3},
    "error_handling":  {"prerequisites": ["functions"],                 "difficulty": 4},
    "lists":           {"prerequisites": ["data_types"],                "difficulty": 2},
    "strings":         {"prerequisites": ["data_types"],                "difficulty": 2},
    "dictionaries":    {"prerequisites": ["lists"],                     "difficulty": 3},
    "sets":            {"prerequisites": ["lists"],                     "difficulty": 3},
    "oop_basics":      {"prerequisites": ["functions"],                 "difficulty": 4},
    "file_io":         {"prerequisites": ["error_handling"],            "difficulty": 4},
    "modules":         {"prerequisites": ["functions"],                 "difficulty": 3},
}

# Mastery threshold to consider a topic "completed" for prerequisite purposes
_PREREQ_MASTERY_THRESHOLD = 0.4   # intermediate or above


class CurriculumEngine:
    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    # ────────────────────────── Mastery helpers ───────────────────────────────

    def _get_student_mastery_map(self, student_id: str) -> dict[str, float]:
        """Return topic_id → score for all recorded topics."""
        summary = self._memory.get_student_summary(student_id)
        return {
            m["topic_id"]: m["score"]
            for m in summary.get("mastery", [])
        }

    def is_unlocked(self, student_id: str, topic_id: str) -> bool:
        """Return True if all prerequisites are satisfied (score >= threshold)."""
        topic = TOPIC_DAG.get(topic_id)
        if not topic:
            return False
        if not topic["prerequisites"]:
            return True  # No prerequisites — always unlocked

        mastery = self._get_student_mastery_map(student_id)
        for prereq in topic["prerequisites"]:
            score = mastery.get(prereq, 0.0)
            if score < _PREREQ_MASTERY_THRESHOLD:
                return False
        return True

    def get_unlocked_topics(self, student_id: str) -> list[str]:
        """Return all topic IDs that the student has unlocked."""
        return [
            tid for tid in TOPIC_DAG
            if self.is_unlocked(student_id, tid)
        ]

    def unlock_topics(self, student_id: str) -> list[str]:
        """Check prerequisites and return newly unlocked topics."""
        unlocked = self.get_unlocked_topics(student_id)
        log.debug("Unlocked topics for student %s: %s", student_id, unlocked)
        return unlocked

    def get_next_topic(self, student_id: str) -> str | None:
        """
        Return the lowest-difficulty unlocked topic not yet mastered.
        'Not yet mastered' means score < threshold.
        """
        mastery = self._get_student_mastery_map(student_id)
        unlocked = self.get_unlocked_topics(student_id)

        candidates: list[tuple[int, str]] = []
        for tid in unlocked:
            score = mastery.get(tid, 0.0)
            if score < _PREREQ_MASTERY_THRESHOLD:
                difficulty = TOPIC_DAG[tid]["difficulty"]
                candidates.append((difficulty, tid))

        if not candidates:
            # All unlocked topics are mastered — look for locked ones with unlockable prereqs
            return None

        # Sort by difficulty, then alphabetically for determinism
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][1]

    def get_mastery_map(self, student_id: str) -> dict[str, dict[str, Any]]:
        """Return a full map of topic → {mastery_level, score, locked} for the dashboard."""
        mastery = self._get_student_mastery_map(student_id)
        result: dict[str, dict[str, Any]] = {}

        for tid, info in TOPIC_DAG.items():
            score = mastery.get(tid, 0.0)
            locked = not self.is_unlocked(student_id, tid)

            if locked:
                level = "locked"
            elif score == 0.0:
                level = "unlocked"
            elif score < 0.2:
                level = "novice"
            elif score < 0.4:
                level = "beginner"
            elif score < 0.6:
                level = "intermediate"
            elif score < 0.8:
                level = "advanced"
            else:
                level = "expert"

            result[tid] = {
                "mastery_level": level,
                "score": round(score, 3),
                "locked": locked,
                "difficulty": info["difficulty"],
                "prerequisites": info["prerequisites"],
            }

        return result

    def get_topic_info(self, topic_id: str) -> dict[str, Any] | None:
        """Return static topic info from the DAG."""
        return TOPIC_DAG.get(topic_id)
