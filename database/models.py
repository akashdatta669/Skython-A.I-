"""
database/models.py — SQLAlchemy ORM models for Skython AI
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    # Allow legacy Python type-hint annotations (e.g. list[...]) alongside
    # SQLAlchemy 2 Mapped[] style — prevents AmbiguousAnnotationError (zlpr).
    __allow_unmapped__ = True


class Student(Base):
    __tablename__ = "students"

    id: str = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name: str = Column(String, nullable=False)
    experience_level: str = Column(String, default="novice")   # novice/beginner/intermediate
    learning_velocity: str = Column(String, default="normal")  # slow/normal/fast
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    mastery_records: list[TopicMastery] = relationship(
        "TopicMastery", back_populates="student", cascade="all, delete-orphan"
    )
    sessions: list[MentorSession] = relationship(
        "MentorSession", back_populates="student", cascade="all, delete-orphan"
    )
    misconceptions: list[Misconception] = relationship(
        "Misconception", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id!r} name={self.name!r}>"


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    student_id: str = Column(String, ForeignKey("students.id"), nullable=False)
    topic_id: str = Column(String, nullable=False)
    mastery_level: str = Column(
        String, default="novice"
    )  # novice→beginner→intermediate→advanced→expert
    score: float = Column(Float, default=0.0)
    successful_exercises: int = Column(Integer, default=0)
    failed_exercises: int = Column(Integer, default=0)
    last_practiced: datetime | None = Column(DateTime, nullable=True)

    student: Student = relationship("Student", back_populates="mastery_records")

    def __repr__(self) -> str:
        return (
            f"<TopicMastery student={self.student_id!r} "
            f"topic={self.topic_id!r} level={self.mastery_level!r}>"
        )


class MentorSession(Base):
    __tablename__ = "mentor_sessions"

    id: str = Column(String, primary_key=True, default=lambda: str(uuid4()))
    student_id: str = Column(String, ForeignKey("students.id"), nullable=False)
    active_topic: str | None = Column(String, nullable=True)
    hint_level: int = Column(Integer, default=0)        # 0=no hint, 1/2/3=hint levels
    current_strategy: str | None = Column(String, nullable=True)  # analogy/code_trace/rubber_duck/hints
    started_at: datetime = Column(DateTime, default=datetime.utcnow)
    ended_at: datetime | None = Column(DateTime, nullable=True)

    student: Student = relationship("Student", back_populates="sessions")
    messages: list[ConversationMessage] = relationship(
        "ConversationMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MentorSession id={self.id!r} topic={self.active_topic!r}>"


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    session_id: str = Column(String, ForeignKey("mentor_sessions.id"), nullable=False)
    role: str = Column(String, nullable=False)      # "student" or "mentor"
    content: str = Column(Text, nullable=False)
    topic: str | None = Column(String, nullable=True)
    message_type: str = Column(String, default="chat")  # chat/code/hint/assessment
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    session: MentorSession = relationship("MentorSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConversationMessage role={self.role!r} type={self.message_type!r}>"


class Misconception(Base):
    __tablename__ = "misconceptions"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    student_id: str = Column(String, ForeignKey("students.id"), nullable=False)
    topic_id: str = Column(String, nullable=False)
    description: str = Column(Text, nullable=False)
    frequency: int = Column(Integer, default=1)
    corrected: bool = Column(Boolean, default=False)
    correction_date: datetime | None = Column(DateTime, nullable=True)
    first_seen: datetime = Column(DateTime, default=datetime.utcnow)

    student: Student = relationship("Student", back_populates="misconceptions")

    def __repr__(self) -> str:
        return (
            f"<Misconception student={self.student_id!r} "
            f"topic={self.topic_id!r} corrected={self.corrected}>"
        )
