"""
NeoPilot Pydantic Schemas
Request/Response models for the REST and WebSocket APIs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class SessionPhase(str, Enum):
    DEMO = "demo"
    EXERCISE = "exercise"
    ASSESSMENT = "assessment"
    ADAPTIVE = "adaptive_path"


class OverlayMode(str, Enum):
    BLINK = "blink"
    SOLID = "solid"
    FADE = "fade"
    PULSE = "pulse"


# ─── Session API ──────────────────────────────────────────────────────────────


class SessionStartRequest(BaseModel):
    """Request to start a new teaching session."""

    app_id: str = Field(..., description="Target application (e.g. 'freecad', 'libreoffice-writer')")
    task_description: str = Field(
        ...,
        description="What the student wants to learn (e.g. 'basic extrusion in FreeCAD')",
        min_length=5,
    )
    user_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional context: skill level, language, preferences",
    )
    language: str = Field(default="pt-BR", description="Teaching language")


class SessionStartResponse(BaseModel):
    """Response after creating a new session."""

    session_id: str
    status: str = "initializing"
    initial_message: str = Field(..., description="First teaching message for the student")
    initial_actions: list[ActionCommand] = Field(
        default_factory=list,
        description="Initial actions for the client to execute",
    )


class ObserveRequest(BaseModel):
    """Client sends current state observation."""

    session_id: str
    screenshot_b64: str = Field(..., description="Base64-encoded WebP screenshot")
    text: Optional[str] = Field(default=None, description="Student's text/voice input")
    audio_b64: Optional[str] = Field(default=None, description="Base64-encoded audio clip")
    app_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Window title, focused element, app state",
    )


class ActionResultRequest(BaseModel):
    """Client reports the result of an executed action."""

    session_id: str
    action_id: str
    success: bool
    screenshot_after_b64: Optional[str] = Field(
        default=None,
        description="Screenshot taken after action execution",
    )
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Action Commands (Backend → Client) ──────────────────────────────────────


class ActionCommand(BaseModel):
    """An action for the client to execute."""

    id: str = Field(default="", description="Unique action ID for tracking")
    type: str = Field(..., description="Action type: click, type_text, hotkey, etc.")
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", description="Human-readable explanation")


class OverlayCommand(BaseModel):
    """An overlay instruction for the client to render."""

    type: str = Field(
        ...,
        description="Overlay type: arrow, highlight, text",
    )
    params: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = Field(default=3000, description="How long to show the overlay")


class TeachingResponse(BaseModel):
    """Full response from the teaching engine to the client."""

    session_id: str
    message: str = Field(default="", description="Teaching explanation for the student")
    actions: list[ActionCommand] = Field(default_factory=list)
    overlays: list[OverlayCommand] = Field(default_factory=list)
    narration: Optional[str] = Field(default=None, description="Text for TTS narration")
    phase: SessionPhase = SessionPhase.DEMO
    progress_pct: float = 0.0
    is_complete: bool = False


# ─── WebSocket Messages ──────────────────────────────────────────────────────


class WSMessage(BaseModel):
    """Base WebSocket message with type discriminator."""

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class WSClientMessage(WSMessage):
    """Message from client → backend."""

    session_id: str


class WSServerMessage(WSMessage):
    """Message from backend → client."""

    pass


# ─── Status & Health ─────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "2.0.0-alpha"
    claude_model: str = ""
    database: str = "connected"
    uptime_seconds: float = 0.0


class SessionStatusResponse(BaseModel):
    """Status of an active session."""

    session_id: str
    state: str
    current_step: int
    total_tokens_used: int
    total_cost_usd: float
    progress_pct: float
    error_count: int
    created_at: datetime
    updated_at: datetime


# ─── Forward reference fix ───────────────────────────────────────────────────
# SessionStartResponse references ActionCommand which is defined after it
SessionStartResponse.model_rebuild()
