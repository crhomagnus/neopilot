"""
NeoPilot Unified Context Builder
Combina screenshot, árvore AT-SPI e DOM em contexto unificado para o LLM.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from neopilot.core.logger import get_logger
from neopilot.perception.accessibility import AccessibilityTree
from neopilot.perception.screen_capture import ScreenCapture, Screenshot
from neopilot.perception.visual_grounder import VisualGrounder

logger = get_logger("context_builder")


@dataclass
class UnifiedContext:
    timestamp: float
    screenshot: Screenshot
    screenshot_b64: str                  # Base64 para envio ao LLM
    active_window: dict[str, Any]
    accessibility_tree: Optional[dict]   # Árvore AT-SPI serializada
    visible_text: str                    # OCR de todo texto visível
    open_applications: list[str]
    cursor_position: tuple[int, int]
    display_server: str

    def to_llm_message(self) -> dict[str, Any]:
        """Formata contexto para envio ao LLM multimodal."""
        return {
            "timestamp": self.timestamp,
            "display_server": self.display_server,
            "active_window": self.active_window,
            "open_applications": self.open_applications,
            "cursor_position": list(self.cursor_position),
            "visible_text_sample": self.visible_text[:2000],
            "accessibility_summary": self._summarize_a11y(),
            "screenshot_base64": self.screenshot_b64,
        }

    def _summarize_a11y(self) -> dict[str, Any]:
        if not self.accessibility_tree:
            return {}
        # Retorna apenas os primeiros 2 níveis para não sobrecarregar o LLM
        def truncate(node: dict, depth: int = 0) -> dict:
            if depth >= 2:
                return {k: v for k, v in node.items() if k != "children"}
            result = dict(node)
            if "children" in result:
                result["children"] = [
                    truncate(c, depth + 1)
                    for c in result["children"][:10]
                ]
            return result

        return truncate(self.accessibility_tree)


class ContextBuilder:
    """Constrói contexto unificado do estado atual da tela."""

    def __init__(self):
        self.screen_capture = ScreenCapture()
        self.accessibility = AccessibilityTree()
        self.grounder = VisualGrounder(use_ui_tars=False)

    def build(
        self,
        monitor: int = 1,
        capture_a11y: bool = True,
        run_ocr: bool = True,
        llm_image_quality: int = 85,
    ) -> UnifiedContext:
        """Captura e integra todas as fontes de percepção."""
        start = time.time()

        # 1. Screenshot
        screenshot = self.screen_capture.capture(monitor=monitor)
        screenshot_resized = screenshot.resize_for_llm(max_size=1920)
        screenshot_b64 = screenshot_resized.to_base64(quality=llm_image_quality)

        # 2. Janela ativa
        active_window = self._get_active_window()

        # 3. AT-SPI
        a11y_dict = None
        if capture_a11y and self.accessibility._pyatspi_available:
            try:
                app_name = active_window.get("name", "")
                app_node = self.accessibility.get_application(app_name)
                if app_node:
                    elem = self.accessibility.build_tree(app_node, max_depth=4)
                    a11y_dict = elem.to_dict() if elem else None
            except Exception as e:
                logger.debug("Falha ao capturar AT-SPI", error=str(e))

        # 4. OCR (texto visível)
        visible_text = ""
        if run_ocr:
            try:
                visible_text = self.grounder.extract_all_text(screenshot)
            except Exception as e:
                logger.debug("Falha no OCR", error=str(e))

        # 5. Apps abertos
        open_apps = self.accessibility.list_applications()

        # 6. Posição do cursor
        cursor_pos = self._get_cursor_position()

        elapsed = time.time() - start
        logger.debug("Contexto construído", elapsed_ms=round(elapsed * 1000))

        return UnifiedContext(
            timestamp=time.time(),
            screenshot=screenshot,
            screenshot_b64=screenshot_b64,
            active_window=active_window,
            accessibility_tree=a11y_dict,
            visible_text=visible_text,
            open_applications=open_apps,
            cursor_position=cursor_pos,
            display_server=self.screen_capture.display_server,
        )

    def _get_active_window(self) -> dict[str, Any]:
        import subprocess
        try:
            if self.screen_capture.display_server == "x11":
                wid = subprocess.check_output(
                    ["xdotool", "getactivewindow"],
                    text=True, timeout=2
                ).strip()
                name = subprocess.check_output(
                    ["xdotool", "getwindowname", wid],
                    text=True, timeout=2
                ).strip()
                pid = subprocess.check_output(
                    ["xdotool", "getwindowpid", wid],
                    text=True, timeout=2
                ).strip()
                return {"id": wid, "name": name, "pid": pid}
        except Exception:
            pass
        return {"id": None, "name": "unknown", "pid": None}

    def _get_cursor_position(self) -> tuple[int, int]:
        import subprocess
        try:
            if self.screen_capture.display_server == "x11":
                out = subprocess.check_output(
                    ["xdotool", "getmouselocation", "--shell"],
                    text=True, timeout=2
                )
                vals = {}
                for line in out.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        vals[k] = int(v)
                return vals.get("X", 0), vals.get("Y", 0)
        except Exception:
            pass
        return (0, 0)
