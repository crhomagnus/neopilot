"""
NeoPilot Thin Client — ACI (Agent-Computer Interface)
Executes mouse/keyboard commands received from the backend.
Supports X11 (xdotool) and has fallback to pyautogui.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class ACIController:
    """
    Agent-Computer Interface controller.
    Executes mouse/keyboard actions on the host system.
    Dispatches actions based on type received from the backend.
    """

    def __init__(self, use_xdotool: bool = True) -> None:
        self.use_xdotool = use_xdotool
        self._verify_tools()

    def _verify_tools(self) -> None:
        """Check which tools are available."""
        self._has_xdotool = False
        try:
            subprocess.run(
                ["xdotool", "--version"],
                capture_output=True,
                timeout=2,
            )
            self._has_xdotool = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        logger.info(
            "aci_initialized",
            xdotool=self._has_xdotool,
            pyautogui=HAS_PYAUTOGUI,
        )

    async def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an action command from the backend.

        Args:
            action: dict with 'type' and 'params' keys.

        Returns:
            dict with 'success', 'error', and optional metadata.
        """
        action_type = action.get("type", "")
        params = action.get("params", {})

        try:
            handler = getattr(self, f"_do_{action_type}", None)
            if handler is None:
                return {"success": False, "error": f"Unknown action: {action_type}"}

            result = handler(**params)
            return {"success": True, "result": result}

        except Exception as e:
            logger.error("aci_action_failed", action=action_type, error=str(e))
            return {"success": False, "error": str(e)}

    def _do_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        **_,
    ) -> str:
        """Execute mouse click."""
        if self._has_xdotool and self.use_xdotool:
            btn_map = {"left": "1", "middle": "2", "right": "3"}
            btn = btn_map.get(button, "1")
            # Move then click
            subprocess.run(["xdotool", "mousemove", str(x), str(y)], timeout=2)
            for _ in range(clicks):
                subprocess.run(["xdotool", "click", btn], timeout=2)
        elif HAS_PYAUTOGUI:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        else:
            raise RuntimeError("No mouse control tool available")

        return f"Clicked ({x}, {y}) button={button} x{clicks}"

    def _do_type_text(self, text: str, delay_ms: int = 20, **_) -> str:
        """Type text via keyboard."""
        if self._has_xdotool and self.use_xdotool:
            subprocess.run(
                ["xdotool", "type", "--delay", str(delay_ms), "--", text],
                timeout=30,
            )
        elif HAS_PYAUTOGUI:
            pyautogui.typewrite(text, interval=delay_ms / 1000)
        else:
            raise RuntimeError("No keyboard control tool available")

        return f"Typed {len(text)} chars"

    def _do_hotkey(self, keys: list[str], **_) -> str:
        """Press key combination."""
        if self._has_xdotool and self.use_xdotool:
            combo = "+".join(keys)
            subprocess.run(["xdotool", "key", combo], timeout=2)
        elif HAS_PYAUTOGUI:
            pyautogui.hotkey(*keys)
        else:
            raise RuntimeError("No keyboard control tool available")

        return f"Hotkey {'+'.join(keys)}"

    def _do_mouse_move(self, x: int, y: int, **_) -> str:
        """Move mouse without clicking."""
        if self._has_xdotool and self.use_xdotool:
            subprocess.run(["xdotool", "mousemove", str(x), str(y)], timeout=2)
        elif HAS_PYAUTOGUI:
            pyautogui.moveTo(x, y)
        else:
            raise RuntimeError("No mouse control tool available")

        return f"Mouse moved to ({x}, {y})"

    def _do_scroll(
        self,
        direction: str,
        amount: int = 3,
        x: Optional[int] = None,
        y: Optional[int] = None,
        **_,
    ) -> str:
        """Scroll at position."""
        if x is not None and y is not None:
            self._do_mouse_move(x, y)

        if self._has_xdotool and self.use_xdotool:
            btn = "4" if direction in ("up", "left") else "5"
            for _ in range(amount):
                subprocess.run(["xdotool", "click", btn], timeout=2)
        elif HAS_PYAUTOGUI:
            scroll_amount = amount if direction in ("up", "left") else -amount
            pyautogui.scroll(scroll_amount)

        return f"Scrolled {direction} x{amount}"

    def _do_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: str = "left",
        **_,
    ) -> str:
        """Click and drag."""
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.mouseDown(button=button)
            pyautogui.moveTo(end_x, end_y, duration=0.5)
            pyautogui.mouseUp(button=button)
        elif self._has_xdotool:
            subprocess.run(["xdotool", "mousemove", str(start_x), str(start_y)], timeout=2)
            subprocess.run(["xdotool", "mousedown", "1"], timeout=2)
            subprocess.run(["xdotool", "mousemove", str(end_x), str(end_y)], timeout=2)
            subprocess.run(["xdotool", "mouseup", "1"], timeout=2)

        return f"Dragged ({start_x},{start_y}) → ({end_x},{end_y})"

    def _do_wait(self, duration_ms: int = 1000, **_) -> str:
        """Wait for specified duration."""
        time.sleep(duration_ms / 1000)
        return f"Waited {duration_ms}ms"

    def _do_request_screenshot(self, **_) -> str:
        """Signal to capture a screenshot (handled by the main loop)."""
        return "screenshot_requested"
