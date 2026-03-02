"""
NeoPilot Thin Client — Screen Capture
Captures screenshots of the active window or full screen using mss.
Compresses to WebP and applies frame differencing.
"""

from __future__ import annotations

import base64
import io
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    import mss
    import mss.tools

    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    logger.warning("mss_not_available", hint="pip install mss")

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("pillow_not_available", hint="pip install Pillow")


class ScreenCapture:
    """
    Captures screenshots and compresses them for network transmission.
    Uses mss for fast screen capture and Pillow for WebP compression.
    """

    def __init__(
        self,
        max_dimension: int = 1920,
        quality: int = 80,
    ) -> None:
        self.max_dimension = max_dimension
        self.quality = quality
        self._sct = mss.mss() if HAS_MSS else None
        self._last_frame: Optional[bytes] = None

    def capture_full_screen(self, monitor: int = 1) -> Optional[str]:
        """
        Capture full screen and return as base64-encoded WebP string.

        Args:
            monitor: Monitor index (0=all, 1=primary, 2=secondary, etc.)

        Returns:
            Base64-encoded WebP image string, or None if capture fails.
        """
        if not self._sct or not HAS_PIL:
            logger.error("capture_unavailable", mss=HAS_MSS, pil=HAS_PIL)
            return None

        try:
            sct_img = self._sct.grab(self._sct.monitors[monitor])
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return self._process_image(img)
        except Exception as e:
            logger.error("capture_failed", error=str(e))
            return None

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[str]:
        """Capture a specific screen region."""
        if not self._sct or not HAS_PIL:
            return None

        try:
            region = {"left": x, "top": y, "width": width, "height": height}
            sct_img = self._sct.grab(region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return self._process_image(img)
        except Exception as e:
            logger.error("region_capture_failed", error=str(e))
            return None

    def _process_image(self, img: Image.Image) -> str:
        """Resize if needed and compress to WebP base64."""
        # Resize if exceeds max dimension
        w, h = img.size
        if max(w, h) > self.max_dimension:
            ratio = self.max_dimension / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Compress to WebP
        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=self.quality)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.debug(
            "screenshot_captured",
            original_size=f"{w}x{h}",
            compressed_size=f"{img.size[0]}x{img.size[1]}",
            bytes=len(buffer.getvalue()),
        )

        return b64

    def close(self) -> None:
        """Release resources."""
        if self._sct:
            self._sct.close()
