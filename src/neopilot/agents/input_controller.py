"""
NeoPilot Input Controller
Controle de mouse e teclado com suporte a X11 (xdotool) e Wayland (ydotool).
"""

from __future__ import annotations

import os
import subprocess
import time
from enum import Enum
from typing import Optional

import pyautogui

from neopilot.core.logger import get_logger

logger = get_logger("input_controller")

# Segurança: desativa PyAutoGUI fail-safe (canto superior esquerdo)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class InputController:
    """
    Controla mouse e teclado detectando automaticamente X11 ou Wayland.
    Usa xdotool para X11 e ydotool para Wayland nativo.
    """

    def __init__(self):
        self.display_server = self._detect_display_server()
        self._check_tools()
        logger.info("InputController iniciado", display_server=self.display_server)

    def _detect_display_server(self) -> str:
        if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
            return "wayland"
        return "x11"

    def _check_tools(self) -> None:
        if self.display_server == "x11":
            if not self._command_exists("xdotool"):
                logger.warning("xdotool não encontrado — instale com: sudo apt install xdotool")
        else:
            if not self._command_exists("ydotool"):
                logger.warning("ydotool não encontrado — instale com: sudo apt install ydotool")

    def _command_exists(self, cmd: str) -> bool:
        return subprocess.run(
            ["which", cmd], capture_output=True
        ).returncode == 0

    # ─── Mouse ─────────────────────────────────────────────────────────────────

    def move(self, x: int, y: int, duration: float = 0.1) -> None:
        """Move cursor para posição absoluta."""
        if self.display_server == "x11":
            subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=True)
        else:
            subprocess.run(
                ["ydotool", "mousemove", "--absolute", f"-x{x}", f"-y{y}"],
                check=True
            )
        time.sleep(duration)

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: MouseButton = MouseButton.LEFT,
        double: bool = False,
    ) -> None:
        """Clica em posição. Se x,y omitidos, clica na posição atual."""
        btn_map = {
            MouseButton.LEFT: ("1", "0xC0"),
            MouseButton.RIGHT: ("3", "0xC2"),
            MouseButton.MIDDLE: ("2", "0xC1"),
        }
        xdotool_btn, ydotool_btn = btn_map[button]

        if x is not None and y is not None:
            self.move(x, y)

        if self.display_server == "x11":
            clicks = 2 if double else 1
            for _ in range(clicks):
                subprocess.run(["xdotool", "click", xdotool_btn], check=True)
                if double:
                    time.sleep(0.05)
        else:
            # ydotool click: 0xC0 = left down+up
            clicks = 2 if double else 1
            for _ in range(clicks):
                subprocess.run(["ydotool", "click", ydotool_btn], check=True)
                if double:
                    time.sleep(0.05)

        logger.debug("Click executado", x=x, y=y, button=button.value, double=double)

    def right_click(self, x: int, y: int) -> None:
        self.click(x, y, button=MouseButton.RIGHT)

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.3,
    ) -> None:
        """Drag & drop de um ponto a outro."""
        if self.display_server == "x11":
            subprocess.run([
                "xdotool", "mousemove", str(from_x), str(from_y),
                "mousedown", "1",
                "mousemove", str(to_x), str(to_y),
                "mouseup", "1"
            ], check=True)
        else:
            pyautogui.moveTo(from_x, from_y)
            pyautogui.dragTo(to_x, to_y, duration=duration, button="left")
        logger.debug("Drag executado", from_=(from_x, from_y), to=(to_x, to_y))

    def scroll(
        self, x: int, y: int, clicks: int = 3, direction: str = "down"
    ) -> None:
        """Scroll na posição indicada."""
        self.move(x, y)
        btn = "4" if direction == "up" else "5"
        if self.display_server == "x11":
            for _ in range(abs(clicks)):
                subprocess.run(["xdotool", "click", btn], check=True)
        else:
            pyautogui.scroll(clicks if direction == "up" else -clicks)

    # ─── Teclado ───────────────────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.02) -> None:
        """Digita texto no elemento focado.
        Usa stdin via --file para evitar problemas com texto que começa com '-'.
        Newlines (\\n) são enviados como xdotool key Return para compatibilidade.
        """
        if self.display_server == "x11":
            # Divide por \\n para enviar Return explicitamente
            segments = text.split("\n")
            for i, segment in enumerate(segments):
                if segment:
                    subprocess.run(
                        ["xdotool", "type", "--clearmodifiers", "--delay", "20", "--file", "-"],
                        input=segment,
                        text=True,
                        check=True,
                    )
                if i < len(segments) - 1:
                    subprocess.run(
                        ["xdotool", "key", "--clearmodifiers", "Return"],
                        check=True,
                    )
        else:
            subprocess.run(["ydotool", "type", "--", text], check=True)
        logger.debug("Texto digitado", length=len(text))

    def press_key(self, key: str) -> None:
        """Pressiona tecla pelo nome (e.g., 'Return', 'Tab', 'ctrl+c')."""
        if self.display_server == "x11":
            subprocess.run(["xdotool", "key", "--clearmodifiers", key], check=True)
        else:
            # ydotool usa keycodes — converte nomes comuns
            keycode = self._key_to_ydotool(key)
            if keycode:
                subprocess.run(["ydotool", "key", keycode], check=True)
            else:
                pyautogui.hotkey(*key.split("+"))
        logger.debug("Tecla pressionada", key=key)

    def hotkey(self, *keys: str) -> None:
        """Atalho de teclado (e.g., 'ctrl', 's')."""
        combo = "+".join(keys)
        self.press_key(combo)

    def _key_to_ydotool(self, key: str) -> Optional[str]:
        """Converte nome de tecla para código ydotool."""
        mapping = {
            "Return": "28",
            "Tab": "15",
            "Escape": "1",
            "ctrl+c": "29:46",
            "ctrl+v": "29:47",
            "ctrl+z": "29:44",
            "ctrl+s": "29:31",
            "ctrl+a": "29:30",
            "Delete": "111",
            "BackSpace": "14",
        }
        return mapping.get(key)

    # ─── Clipboard ─────────────────────────────────────────────────────────────

    def copy_to_clipboard(self, text: str) -> None:
        """Coloca texto no clipboard."""
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode(),
            check=True,
        )

    def get_clipboard(self) -> str:
        """Lê conteúdo do clipboard."""
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True,
            text=True,
        )
        return result.stdout

    def paste_from_clipboard(self) -> None:
        """Cola conteúdo do clipboard no campo focado."""
        self.hotkey("ctrl", "v")
