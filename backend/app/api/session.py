"""
NeoPilot REST API — Session Endpoints
Handles session creation, observation, and action results.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models.schemas import (
    ActionResultRequest,
    ObserveRequest,
    SessionStartRequest,
    SessionStartResponse,
    SessionStatusResponse,
    TeachingResponse,
)
from backend.app.services.session_manager import SessionManager
from backend.app.services.claude_client import ClaudeClient

router = APIRouter(prefix="/session", tags=["session"])

# Singleton service instances (initialized at app startup)
_claude_client: ClaudeClient | None = None
_session_manager: SessionManager | None = None


def init_services() -> None:
    """Initialize service singletons. Called during app startup."""
    global _claude_client, _session_manager
    _claude_client = ClaudeClient()
    _session_manager = SessionManager(_claude_client)


def get_session_manager() -> SessionManager:
    """Dependency to get the session manager."""
    if _session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Services not initialized",
        )
    return _session_manager


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/start",
    response_model=TeachingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new teaching session",
    description="Creates a new session, initializes Claude conversation, returns initial teaching plan.",
)
async def start_session(
    request: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    manager: SessionManager = Depends(get_session_manager),
):
    try:
        session, response = await manager.create_session(
            db=db,
            app_id=request.app_id,
            task_description=request.task_description,
            user_context=request.user_context,
            language=request.language,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.post(
    "/observe",
    response_model=TeachingResponse,
    summary="Send observation to teaching engine",
    description="Client sends a screenshot (and optional text/audio) for the teaching engine to process.",
)
async def observe(
    request: ObserveRequest,
    db: AsyncSession = Depends(get_db),
    manager: SessionManager = Depends(get_session_manager),
):
    try:
        response = await manager.process_observation(
            db=db,
            session_id=request.session_id,
            screenshot_b64=request.screenshot_b64,
            text=request.text,
            app_metadata=request.app_metadata,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Observation processing failed: {str(e)}",
        )


@router.post(
    "/action-result",
    response_model=TeachingResponse,
    summary="Report action execution result",
    description="Client reports whether an action was executed successfully, with optional post-action screenshot.",
)
async def action_result(
    request: ActionResultRequest,
    db: AsyncSession = Depends(get_db),
    manager: SessionManager = Depends(get_session_manager),
):
    try:
        response = await manager.process_action_result(
            db=db,
            session_id=request.session_id,
            action_id=request.action_id,
            success=request.success,
            screenshot_after_b64=request.screenshot_after_b64,
            error_message=request.error_message,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action result processing failed: {str(e)}",
        )


@router.get(
    "/{session_id}/status",
    summary="Get session status",
    description="Returns detailed status of an active teaching session.",
)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    manager: SessionManager = Depends(get_session_manager),
):
    try:
        return await manager.get_session_status(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
