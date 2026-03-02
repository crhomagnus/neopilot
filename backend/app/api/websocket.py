"""
NeoPilot WebSocket API
Real-time bidirectional communication for teaching sessions.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import async_session_factory
from backend.app.api.session import get_session_manager
from backend.app.services.session_manager import SessionManager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}  # session_id → ws

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("ws_client_connected", session_id=session_id)

    def disconnect(self, session_id: str) -> None:
        self.active_connections.pop(session_id, None)
        logger.info("ws_client_disconnected", session_id=session_id)

    async def send_json(self, session_id: str, data: dict[str, Any]) -> None:
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(data)

    async def broadcast(self, data: dict[str, Any]) -> None:
        for ws in self.active_connections.values():
            await ws.send_json(data)


conn_manager = ConnectionManager()


@router.websocket("/session/stream")
async def session_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time teaching sessions.

    Client message protocol:
        {"type": "observe", "session_id": "...", "screenshot_b64": "...", "text": "..."}
        {"type": "action_result", "session_id": "...", "action_id": "...", "success": true}
        {"type": "ping"}

    Server message protocol:
        {"type": "teaching", "data": <TeachingResponse>}
        {"type": "error", "message": "..."}
        {"type": "pong"}
    """
    await websocket.accept()
    session_id: str | None = None
    manager = get_session_manager()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
                continue

            session_id = msg.get("session_id")
            if not session_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "session_id is required",
                })
                continue

            # Track connection
            conn_manager.active_connections[session_id] = websocket

            async with async_session_factory() as db:
                try:
                    if msg_type == "observe":
                        response = await manager.process_observation(
                            db=db,
                            session_id=session_id,
                            screenshot_b64=msg.get("screenshot_b64", ""),
                            text=msg.get("text"),
                            app_metadata=msg.get("app_metadata", {}),
                        )
                        await websocket.send_json({
                            "type": "teaching",
                            "data": response.model_dump(),
                        })

                    elif msg_type == "action_result":
                        response = await manager.process_action_result(
                            db=db,
                            session_id=session_id,
                            action_id=msg.get("action_id", ""),
                            success=msg.get("success", False),
                            screenshot_after_b64=msg.get("screenshot_after_b64"),
                            error_message=msg.get("error_message"),
                        )
                        await websocket.send_json({
                            "type": "teaching",
                            "data": response.model_dump(),
                        })

                    elif msg_type == "status":
                        status_data = await manager.get_session_status(db, session_id)
                        await websocket.send_json({
                            "type": "status",
                            "data": status_data,
                        })

                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}",
                        })

                except ValueError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })
                except Exception as e:
                    logger.error(
                        "ws_processing_error",
                        session_id=session_id,
                        error=str(e),
                        msg_type=msg_type,
                    )
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Processing error: {str(e)}",
                    })

    except WebSocketDisconnect:
        if session_id:
            conn_manager.disconnect(session_id)
    except json.JSONDecodeError:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid JSON",
        })
    except Exception as e:
        logger.error("ws_unexpected_error", error=str(e))
        if session_id:
            conn_manager.disconnect(session_id)
