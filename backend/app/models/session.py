"""
NeoPilot SQLAlchemy Models
Session, ActionLog, StudentState for the teaching engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship

from backend.app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────


class SessionState(str, PyEnum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEMO = "demo"
    EXERCISE = "exercise"
    ASSESSMENT = "assessment"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class ActionType(str, PyEnum):
    CLICK = "click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    SCREENSHOT = "screenshot"
    OVERLAY = "overlay"
    SPEAK = "speak"
    ASK = "ask"
    EVALUATE = "evaluate"
    NAVIGATE = "navigate"
    WAIT = "wait"


# ─── Models ───────────────────────────────────────────────────────────────────


class Session(Base):
    """A teaching session between NeoPilot and a student."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_new_id)
    app_id = Column(String(100), nullable=False, doc="Target application identifier")
    task_description = Column(Text, nullable=False)
    state = Column(
        Enum(SessionState),
        default=SessionState.INITIALIZING,
        nullable=False,
    )
    user_context = Column(JSON, default=dict)
    claude_conversation = Column(JSON, default=list, doc="Full Claude message history")
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    current_step = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    action_logs = relationship("ActionLog", back_populates="session", cascade="all, delete-orphan")
    student_state = relationship(
        "StudentState",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ActionLog(Base):
    """Log entry for each action executed during a session."""

    __tablename__ = "action_logs"

    id = Column(String(36), primary_key=True, default=_new_id)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    step = Column(Integer, nullable=False)
    action_type = Column(Enum(ActionType), nullable=False)
    payload = Column(JSON, default=dict, doc="Action parameters as JSON")
    result = Column(JSON, default=dict, doc="Execution result from client")
    success = Column(Boolean, default=None, nullable=True)
    latency_ms = Column(Float, default=None, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    session = relationship("Session", back_populates="action_logs")


class StudentState(Base):
    """Tracks the student's learning progress within a session."""

    __tablename__ = "student_states"

    id = Column(String(36), primary_key=True, default=_new_id)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, unique=True)
    lesson_id = Column(String(100), default="")
    progress_pct = Column(Float, default=0.0)
    errors_made = Column(Integer, default=0)
    correct_actions = Column(Integer, default=0)
    knowledge_map = Column(JSON, default=dict, doc="Concepts mastered by student")
    current_phase = Column(String(50), default="demo")
    hints_given = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    session = relationship("Session", back_populates="student_state")
