"""
engines/memory_manager.py — State persistence and conversation history
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from config import get_mastery_level, MASTERY_PROMOTION_MIN_EXERCISES, MASTERY_PROMOTION_MIN_SCORE
from database.db import get_db, get_db_write
from database.models import (
    ConversationMessage,
    Misconception,
    MentorSession,
    Student,
    TopicMastery,
)

log = logging.getLogger(__name__)


class MemoryManager:
    """Thread-safe persistence layer for all student state."""

    # ────────────────────────── Student ───────────────────────────────────────

    def get_or_create_student(self, name: str) -> Student:
        with get_db_write() as db:
            student = db.query(Student).filter(Student.name == name).first()
            if not student:
                student = Student(name=name)
                db.add(student)
                db.flush()
                log.info("Created new student: %s (id=%s)", name, student.id)
            return student

    def get_student(self, student_id: str) -> Student | None:
        with get_db() as db:
            return db.query(Student).filter(Student.id == student_id).first()

    def update_student(self, student_id: str, **kwargs: Any) -> None:
        with get_db_write() as db:
            db.query(Student).filter(Student.id == student_id).update(kwargs)

    # ────────────────────────── Sessions ──────────────────────────────────────

    def create_session(self, student_id: str, topic: str | None = None) -> MentorSession:
        with get_db_write() as db:
            session = MentorSession(student_id=student_id, active_topic=topic)
            db.add(session)
            db.flush()
            log.info("Created session %s for student %s", session.id, student_id)
            return session

    def get_session(self, session_id: str) -> MentorSession | None:
        with get_db() as db:
            return (
                db.query(MentorSession)
                .filter(MentorSession.id == session_id)
                .first()
            )

    def update_session(self, session_id: str, **kwargs: Any) -> None:
        with get_db_write() as db:
            db.query(MentorSession).filter(MentorSession.id == session_id).update(kwargs)

    def end_session(self, session_id: str) -> None:
        self.update_session(session_id, ended_at=datetime.utcnow())

    # ────────────────────────── Messages ──────────────────────────────────────

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        topic: str | None = None,
        message_type: str = "chat",
    ) -> None:
        with get_db_write() as db:
            msg = ConversationMessage(
                session_id=session_id,
                role=role,
                content=content,
                topic=topic,
                message_type=message_type,
            )
            db.add(msg)

    def get_context(self, session_id: str, n: int = 20) -> list[dict[str, Any]]:
        """Return the last N messages for a session as list of dicts."""
        with get_db() as db:
            msgs = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(n)
                .all()
            )
        return [
            {
                "role": m.role,
                "content": m.content,
                "topic": m.topic,
                "type": m.message_type,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in reversed(msgs)
        ]

    # ────────────────────────── Mastery ───────────────────────────────────────

    def get_mastery(self, student_id: str, topic_id: str) -> TopicMastery | None:
        with get_db() as db:
            return (
                db.query(TopicMastery)
                .filter(
                    TopicMastery.student_id == student_id,
                    TopicMastery.topic_id == topic_id,
                )
                .first()
            )

    def update_mastery(
        self, student_id: str, topic_id: str, success: bool
    ) -> TopicMastery:
        """
        EMA update for mastery score.
        Success: new_score = current * 0.7 + 1.0 * 0.3
        Failure: new_score = current * 0.7 + 0.0 * 0.3
        Promote level when score >= 0.8 AND successful_exercises >= 3
        """
        with get_db_write() as db:
            record = (
                db.query(TopicMastery)
                .filter(
                    TopicMastery.student_id == student_id,
                    TopicMastery.topic_id == topic_id,
                )
                .first()
            )

            if not record:
                record = TopicMastery(
                    student_id=student_id,
                    topic_id=topic_id,
                )
                db.add(record)
                db.flush()

            # EMA update
            if success:
                record.score = (record.score * 0.7) + (1.0 * 0.3)
                record.successful_exercises += 1
            else:
                record.score = (record.score * 0.7) + (0.0 * 0.3)
                record.failed_exercises += 1

            record.score = max(0.0, min(1.0, record.score))
            record.last_practiced = datetime.utcnow()

            # Level promotion
            new_level = get_mastery_level(record.score)
            if (
                record.score >= MASTERY_PROMOTION_MIN_SCORE
                and record.successful_exercises >= MASTERY_PROMOTION_MIN_EXERCISES
            ):
                new_level = "expert" if record.score >= 0.9 else "advanced"

            if record.mastery_level != new_level:
                log.info(
                    "Mastery level change: %s/%s %s → %s",
                    student_id,
                    topic_id,
                    record.mastery_level,
                    new_level,
                )
                record.mastery_level = new_level

            return record

    def get_student_summary(self, student_id: str) -> dict[str, Any]:
        """Return all mastery and misconceptions for a student."""
        with get_db() as db:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return {}

            mastery_records = (
                db.query(TopicMastery)
                .filter(TopicMastery.student_id == student_id)
                .all()
            )
            misconceptions = (
                db.query(Misconception)
                .filter(Misconception.student_id == student_id)
                .all()
            )
            sessions = (
                db.query(MentorSession)
                .filter(MentorSession.student_id == student_id)
                .count()
            )

        return {
            "student": {
                "id": student.id,
                "name": student.name,
                "experience_level": student.experience_level,
                "learning_velocity": student.learning_velocity,
                "created_at": student.created_at.isoformat() if student.created_at else "",
            },
            "mastery": [
                {
                    "topic_id": m.topic_id,
                    "mastery_level": m.mastery_level,
                    "score": round(m.score, 3),
                    "successful": m.successful_exercises,
                    "failed": m.failed_exercises,
                    "last_practiced": m.last_practiced.isoformat() if m.last_practiced else None,
                }
                for m in mastery_records
            ],
            "misconceptions": [
                {
                    "topic_id": mc.topic_id,
                    "description": mc.description,
                    "frequency": mc.frequency,
                    "corrected": mc.corrected,
                }
                for mc in misconceptions
            ],
            "total_sessions": sessions,
        }

    # ────────────────────────── Misconceptions ────────────────────────────────

    def log_misconception(
        self, student_id: str, topic_id: str, description: str
    ) -> None:
        with get_db_write() as db:
            existing = (
                db.query(Misconception)
                .filter(
                    Misconception.student_id == student_id,
                    Misconception.topic_id == topic_id,
                    Misconception.description == description,
                )
                .first()
            )
            if existing:
                existing.frequency += 1
            else:
                db.add(
                    Misconception(
                        student_id=student_id,
                        topic_id=topic_id,
                        description=description,
                    )
                )

    def correct_misconception(
        self, student_id: str, topic_id: str, description: str
    ) -> None:
        with get_db_write() as db:
            db.query(Misconception).filter(
                Misconception.student_id == student_id,
                Misconception.topic_id == topic_id,
                Misconception.description == description,
            ).update({"corrected": True, "correction_date": datetime.utcnow()})
