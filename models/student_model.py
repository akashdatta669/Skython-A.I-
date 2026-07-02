"""
models/student_model.py — Student profile and mastery tracking domain model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MasteryRecord:
    topic_id: str
    mastery_level: str = "novice"
    score: float = 0.0
    successful_exercises: int = 0
    failed_exercises: int = 0

    @property
    def total_exercises(self) -> int:
        return self.successful_exercises + self.failed_exercises

    @property
    def success_rate(self) -> float:
        if self.total_exercises == 0:
            return 0.0
        return self.successful_exercises / self.total_exercises

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "mastery_level": self.mastery_level,
            "score": round(self.score, 3),
            "successful_exercises": self.successful_exercises,
            "failed_exercises": self.failed_exercises,
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class StudentProfile:
    """In-memory student profile assembled from database records."""
    id: str
    name: str
    experience_level: str = "novice"
    learning_velocity: str = "normal"
    mastery_records: dict[str, MasteryRecord] = field(default_factory=dict)
    misconceptions: list[dict[str, Any]] = field(default_factory=list)
    total_sessions: int = 0

    @property
    def overall_score(self) -> float:
        if not self.mastery_records:
            return 0.0
        scores = [r.score for r in self.mastery_records.values()]
        return sum(scores) / len(scores)

    @property
    def topics_mastered(self) -> list[str]:
        return [
            tid for tid, r in self.mastery_records.items()
            if r.mastery_level in ("advanced", "expert")
        ]

    def get_mastery(self, topic_id: str) -> MasteryRecord:
        if topic_id not in self.mastery_records:
            self.mastery_records[topic_id] = MasteryRecord(topic_id=topic_id)
        return self.mastery_records[topic_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "experience_level": self.experience_level,
            "learning_velocity": self.learning_velocity,
            "overall_score": round(self.overall_score, 3),
            "topics_mastered": self.topics_mastered,
            "total_sessions": self.total_sessions,
            "mastery_records": {
                tid: r.to_dict() for tid, r in self.mastery_records.items()
            },
        }

    @classmethod
    def from_summary(cls, summary: dict[str, Any]) -> StudentProfile:
        """Build a StudentProfile from a MemoryManager.get_student_summary() dict."""
        student = summary.get("student", {})
        profile = cls(
            id=student.get("id", ""),
            name=student.get("name", "Student"),
            experience_level=student.get("experience_level", "novice"),
            learning_velocity=student.get("learning_velocity", "normal"),
            total_sessions=summary.get("total_sessions", 0),
            misconceptions=summary.get("misconceptions", []),
        )
        for m in summary.get("mastery", []):
            profile.mastery_records[m["topic_id"]] = MasteryRecord(
                topic_id=m["topic_id"],
                mastery_level=m["mastery_level"],
                score=m["score"],
                successful_exercises=m["successful"],
                failed_exercises=m["failed"],
            )
        return profile
