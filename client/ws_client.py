"""
NeoPilot Thin Client — WebSocket Connection
Manages bidirectional communication with the NeoPilot backend.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class WSClient:
    """
    WebSocket client for the NeoPilot backend.
    Handles auto-reconnect, message routing, and binary frame support.
    """

    def __init__(
        self,
        backend_url: str = "ws://localhost:8000/session/stream",
        session_id: Optional[str] = None,
        on_teaching: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> None:
        self.url = backend_url
        self.session_id = session_id
        self._on_teaching = on_teaching
        self._on_error = on_error
        self._ws = None
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0

    async def connect(self) -> None:
        """Connect to the backend WebSocket with auto-reconnect."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets_not_installed", hint="pip install websockets")
            return

        self._running = True
        while self._running:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0
                    logger.info("ws_connected", url=self.url)

                    async for raw_message in ws:
                        try:
                            msg = json.loads(raw_message)
                            await self._handle_message(msg)
                        except json.JSONDecodeError:
                            logger.warning("ws_invalid_json", data=raw_message[:100])

            except Exception as e:
                logger.warning(
                    "ws_connection_lost",
                    error=str(e),
                    reconnect_in=self._reconnect_delay,
                )
                self._ws = None
                if self._running:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2, self._max_reconnect_delay
                    )

    async def _handle_message(self, msg: dict[str, Any]) -> None:
        """Route incoming messages to handlers."""
        msg_type = msg.get("type", "")

        if msg_type == "teaching" and self._on_teaching:
            await self._on_teaching(msg.get("data", {}))
        elif msg_type == "error" and self._on_error:
            await self._on_error(msg.get("message", "Unknown error"))
        elif msg_type == "pong":
            pass  # heartbeat response

    async def send_observe(
        self,
        screenshot_b64: str,
        text: Optional[str] = None,
        app_metadata: Optional[dict] = None,
    ) -> None:
        """Send a screen observation to the backend."""
        if not self._ws:
            logger.warning("ws_not_connected", action="send_observe")
            return

        msg = {
            "type": "observe",
            "session_id": self.session_id,
            "screenshot_b64": screenshot_b64,
        }
        if text:
            msg["text"] = text
        if app_metadata:
            msg["app_metadata"] = app_metadata

        await self._ws.send(json.dumps(msg))

    async def send_action_result(
        self,
        action_id: str,
        success: bool,
        screenshot_after_b64: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Report an action execution result to the backend."""
        if not self._ws:
            logger.warning("ws_not_connected", action="send_action_result")
            return

        msg = {
            "type": "action_result",
            "session_id": self.session_id,
            "action_id": action_id,
            "success": success,
        }
        if screenshot_after_b64:
            msg["screenshot_after_b64"] = screenshot_after_b64
        if error_message:
            msg["error_message"] = error_message

        await self._ws.send(json.dumps(msg))

    async def ping(self) -> None:
        """Send heartbeat ping."""
        if self._ws:
            await self._ws.send(json.dumps({"type": "ping"}))

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("ws_disconnected")
