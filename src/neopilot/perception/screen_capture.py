"""
NeoPilot Screen Capture
Captura de tela com suporte a X11 e Wayland.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image


@dataclass
class Screenshot:
    image: np.ndarray          # BGR numpy array
    pil_image: Image.Image
    width: int
    height: int
    display_server: str        # "x11" | "wayland"
    monitor_index: int = 0
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def save(self, path: str | Path) -> None:
        cv2.imwrite(str(path), self.image)

    def crop(self, x: int, y: int, w: int, h: int) -> "Screenshot":
        cropped = self.image[y:y+h, x:x+w]
        pil = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
        return Screenshot(
            image=cropped,
            pil_image=pil,
            width=w,
            height=h,
            display_server=self.display_server,
            monitor_index=self.monitor_index,
        )

    def to_base64(self, quality: int = 85) -> str:
        import base64
        import io
        buf = io.BytesIO()
        self.pil_image.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode()

    def resize_for_llm(self, max_size: int = 1920) -> "Screenshot":
        """Redimensiona para envio ao LLM reduzindo custo de tokens."""
        h, w = self.image.shape[:2]
        if max(w, h) <= max_size:
            return self
        scale = max_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(self.image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        pil = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
        return Screenshot(
            image=resized,
            pil_image=pil,
            width=new_w,
            height=new_h,
            display_server=self.display_server,
        )


class ScreenCapture:
    """Captura de tela com detecção automática de servidor de display."""

    def __init__(self):
        self.display_server = self._detect_display_server()
        self._mss = None

    def _detect_display_server(self) -> str:
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("DISPLAY"):
            return "x11"
        raise EnvironmentError(
            "Nenhum servidor de display detectado. "
            "Verifique $DISPLAY ou $WAYLAND_DISPLAY."
        )

    def _get_mss(self):
        if self._mss is None:
            import mss
            self._mss = mss.mss()
        return self._mss

    def capture(self, monitor: int = 1) -> Screenshot:
        """Captura tela completa."""
        if self.display_server == "x11":
            return self._capture_x11(monitor)
        else:
            return self._capture_wayland(monitor)

    def _capture_x11(self, monitor: int) -> Screenshot:
        sct = self._get_mss()
        monitor_info = sct.monitors[monitor]
        raw = sct.grab(monitor_info)

        img = np.array(raw)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        pil = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        return Screenshot(
            image=img_bgr,
            pil_image=pil,
            width=raw.width,
            height=raw.height,
            display_server="x11",
            monitor_index=monitor,
        )

    def _capture_wayland(self, monitor: int) -> Screenshot:
        # Usa grim para captura no Wayland
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["grim", tmp_path],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                # Fallback: tenta via XWayland com mss
                return self._capture_x11(monitor)

            img = cv2.imread(tmp_path)
            pil = Image.open(tmp_path).convert("RGB")
            h, w = img.shape[:2]

            return Screenshot(
                image=img,
                pil_image=pil,
                width=w,
                height=h,
                display_server="wayland",
                monitor_index=monitor,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def capture_region(self, x: int, y: int, w: int, h: int) -> Screenshot:
        """Captura região específica da tela."""
        full = self.capture()
        return full.crop(x, y, w, h)

    def capture_window(self, window_id: Optional[int] = None) -> Screenshot:
        """Captura janela específica pelo ID (X11)."""
        if self.display_server != "x11":
            return self.capture()

        if window_id is None:
            # Obtém janela ativa
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True
            )
            window_id = int(result.stdout.strip())

        # Obtém geometria da janela
        result = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", str(window_id)],
            capture_output=True, text=True
        )
        geo = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                geo[k] = int(v)

        return self.capture_region(
            geo.get("X", 0), geo.get("Y", 0),
            geo.get("WIDTH", 800), geo.get("HEIGHT", 600)
        )

    def list_monitors(self) -> list[dict]:
        """Lista monitores disponíveis."""
        sct = self._get_mss()
        return [
            {
                "index": i,
                "left": m["left"],
                "top": m["top"],
                "width": m["width"],
                "height": m["height"],
            }
            for i, m in enumerate(sct.monitors)
        ]
