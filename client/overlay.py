"""
NeoPilot Thin Client — Overlay Engine
Renders teaching overlays (arrows, highlights, text) on a transparent window.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class OverlayItem:
    """A single overlay element to render."""

    type: str  # "arrow", "highlight", "text", "clear_all"
    params: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 3000
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) * 1000 > self.duration_ms


class OverlayEngine:
    """
    Manages teaching overlay items.
    In Phase 0, this is a headless engine that stores overlay state.
    Full rendering (transparent window with Qt/GTK) comes in Phase 4.
    """

    def __init__(self) -> None:
        self._items: list[OverlayItem] = []

    def add_overlay(self, overlay_data: dict[str, Any]) -> None:
        """Add an overlay from a backend command."""
        overlay_type = overlay_data.get("type", "")

        if overlay_type == "clear_overlays":
            self.clear_all()
            return

        item = OverlayItem(
            type=overlay_type,
            params=overlay_data.get("params", {}),
            duration_ms=overlay_data.get("duration_ms", 3000),
        )
        self._items.append(item)

        logger.debug(
            "overlay_added",
            type=overlay_type,
            duration_ms=item.duration_ms,
            total_active=len(self._items),
        )

    def get_active_overlays(self) -> list[OverlayItem]:
        """Get all non-expired overlay items."""
        self._items = [item for item in self._items if not item.is_expired]
        return list(self._items)

    def clear_all(self) -> None:
        """Remove all overlays."""
        count = len(self._items)
        self._items.clear()
        logger.debug("overlays_cleared", removed=count)

    @property
    def active_count(self) -> int:
        """Number of active (non-expired) overlays."""
        return len(self.get_active_overlays())
