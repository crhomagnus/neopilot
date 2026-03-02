"""
NeoPilot Thin Client — Main Entry Point
Connects to the backend, captures screen, executes actions, renders overlays.
"""

from __future__ import annotations

import asyncio
import signal
from typing import Any, Optional

import structlog

from client.aci import ACIController
from client.capture import ScreenCapture
from client.overlay import OverlayEngine
from client.ws_client import WSClient

logger = structlog.get_logger(__name__)


class NeoPilotClient:
    """
    The thin client that connects to the NeoPilot backend.
    Captures screen, sends observations, executes ACI commands,
    and manages teaching overlays.
    """

    def __init__(
        self,
        backend_url: str = "ws://localhost:8000/session/stream",
        session_id: Optional[str] = None,
        capture_interval: float = 2.0,
    ) -> None:
        self.session_id = session_id
        self.capture_interval = capture_interval
        self._running = False

        # Components
        self.capture = ScreenCapture()
        self.aci = ACIController()
        self.overlay = OverlayEngine()
        self.ws = WSClient(
            backend_url=backend_url,
            session_id=session_id,
            on_teaching=self._handle_teaching,
            on_error=self._handle_error,
        )

    async def _handle_teaching(self, data: dict[str, Any]) -> None:
        """Handle a teaching response from the backend."""
        # Process message
        message = data.get("message", "")
        if message:
            logger.info("teacher_says", message=message[:200])

        # Execute ACI actions
        for action in data.get("actions", []):
            action_type = action.get("type", "")

            if action_type == "request_screenshot":
                # Backend wants a fresh screenshot
                screenshot = self.capture.capture_full_screen()
                if screenshot:
                    await self.ws.send_observe(screenshot)
                continue

            if action_type == "ask_student":
                # Interactive question — for now, log it
                question = action.get("params", {}).get("question", "")
                logger.info("teacher_asks", question=question)
                # TODO: Implement user input collection
                continue

            if action_type == "speak":
                # TTS — for now, log it
                text = action.get("params", {}).get("text", "")
                logger.info("teacher_speaks", text=text[:100])
                # TODO: Implement TTS
                continue

            # Execute ACI action
            result = await self.aci.execute_action(action)

            # Report result to backend
            screenshot_after = None
            if result.get("success"):
                # Capture screenshot after action for verification
                await asyncio.sleep(0.3)  # Wait for UI to update
                screenshot_after = self.capture.capture_full_screen()

            await self.ws.send_action_result(
                action_id=action.get("id", ""),
                success=result.get("success", False),
                screenshot_after_b64=screenshot_after,
                error_message=result.get("error"),
            )

        # Process overlay commands
        for overlay in data.get("overlays", []):
            self.overlay.add_overlay(overlay)

    async def _handle_error(self, error_msg: str) -> None:
        """Handle an error from the backend."""
        logger.error("backend_error", message=error_msg)

    async def start(self) -> None:
        """Start the client: connect to backend and begin the teaching loop."""
        self._running = True
        logger.info(
            "client_starting",
            session_id=self.session_id,
            backend=self.ws.url,
        )

        # Run WebSocket connection in the background
        ws_task = asyncio.create_task(self.ws.connect())

        # Wait a moment for connection
        await asyncio.sleep(1)

        # Send initial screenshot
        screenshot = self.capture.capture_full_screen()
        if screenshot and self.session_id:
            await self.ws.send_observe(
                screenshot_b64=screenshot,
                text="Cliente conectado. Pronto para aprender!",
            )

        # Keep running until stopped
        try:
            await ws_task
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Stop the client gracefully."""
        self._running = False
        await self.ws.disconnect()
        self.capture.close()
        logger.info("client_stopped")


async def main():
    """CLI entry point for the thin client."""
    import argparse

    parser = argparse.ArgumentParser(description="NeoPilot Thin Client")
    parser.add_argument("--backend", default="ws://localhost:8000/session/stream")
    parser.add_argument("--session-id", required=True, help="Session ID to connect to")
    args = parser.parse_args()

    client = NeoPilotClient(
        backend_url=args.backend,
        session_id=args.session_id,
    )

    # Handle signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(client.stop()))

    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
