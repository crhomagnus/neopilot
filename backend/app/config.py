"""
NeoPilot Backend Configuration
Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClaudeModel(str, Enum):
    OPUS_4_6 = "claude-opus-4-6"
    SONNET_4 = "claude-sonnet-4-20250514"
    HAIKU_3_5 = "claude-haiku-4-20250514"


class BackendSettings(BaseSettings):
    """Backend configuration via environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="NEOPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────
    app_name: str = "NeoPilot Backend"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"

    # ─── Claude / Anthropic ───────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: ClaudeModel = ClaudeModel.SONNET_4
    claude_max_tokens: int = 8192
    claude_context_window: int = 200_000
    claude_temperature: float = 0.1
    claude_enable_thinking: bool = True
    claude_thinking_budget: int = 10_000
    claude_enable_caching: bool = True

    # ─── Database ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./neopilot.db"

    # ─── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False  # Disabled by default; enable when Redis is available

    # ─── Session ──────────────────────────────────────────────────────────
    session_timeout_seconds: int = 3600  # 1 hour
    max_steps_per_session: int = 200
    screenshot_max_size: int = 1920  # Max dimension for screenshot resize
    screenshot_quality: int = 80  # WebP quality

    # ─── Rate Limiting ────────────────────────────────────────────────────
    daily_api_limit_usd: float = 50.0
    max_requests_per_minute: int = 60


settings = BackendSettings()
