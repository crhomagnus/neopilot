"""
NeoPilot Configuration Manager
Carrega e valida configurações via Pydantic Settings.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentMode(str, Enum):
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    XAI = "xai"
    GOOGLE = "google"


class STTEngine(str, Enum):
    FASTER_WHISPER = "faster-whisper"
    WHISPER = "whisper"


class TTSEngine(str, Enum):
    PYTTSX3 = "pyttsx3"
    ELEVENLABS = "elevenlabs"


class SandboxMode(str, Enum):
    NONE = "none"
    DOCKER = "docker"
    FIREJAIL = "firejail"
    BUBBLEWRAP = "bubblewrap"


# ─── Sub-models ────────────────────────────────────────────────────────────────

class LLMConfig(BaseModel):
    provider: LLMProvider = LLMProvider.ANTHROPIC
    model: str = "claude-sonnet-4-6"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=200000)
    api_key: Optional[str] = None


class LLMSettings(BaseModel):
    primary: LLMConfig = LLMConfig()
    fallback: LLMConfig = LLMConfig(
        provider=LLMProvider.OLLAMA,
        model="qwen2.5-vl:7b",
    )


class STTConfig(BaseModel):
    engine: STTEngine = STTEngine.FASTER_WHISPER
    model: str = "medium"
    language: str = "pt"
    device: str = "cpu"
    vad_enabled: bool = True
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class TTSConfig(BaseModel):
    engine: TTSEngine = TTSEngine.PYTTSX3
    voice_id: str = ""
    rate: int = Field(default=175, ge=50, le=400)
    volume: float = Field(default=0.9, ge=0.0, le=1.0)
    elevenlabs_voice_id: Optional[str] = None


class VoiceSettings(BaseModel):
    stt: STTConfig = STTConfig()
    tts: TTSConfig = TTSConfig()
    hotkey: str = "ctrl+space"
    push_to_talk_key: str = "ctrl+shift+space"


class SecuritySettings(BaseModel):
    sandbox: SandboxMode = SandboxMode.FIREJAIL
    allowed_directories: list[str] = [
        "~/Documents",
        "~/Downloads",
        "~/Desktop",
    ]
    blocked_directories: list[str] = [
        "~/.ssh",
        "~/.gnupg",
    ]
    require_confirmation_for: list[str] = [
        "delete_file",
        "send_email",
        "form_submit",
        "execute_script",
    ]
    daily_api_limit_usd: float = Field(default=5.0, ge=0.0)

    def is_path_allowed(self, path: str | Path) -> bool:
        resolved = Path(path).expanduser().resolve()
        for blocked in self.blocked_directories:
            if resolved.is_relative_to(Path(blocked).expanduser().resolve()):
                return False
        for allowed in self.allowed_directories:
            if resolved.is_relative_to(Path(allowed).expanduser().resolve()):
                return True
        return False

    def requires_confirmation(self, action_type: str) -> bool:
        return action_type in self.require_confirmation_for


class MemorySettings(BaseModel):
    episodic_retention_days: int = 90
    semantic_embedding_model: str = "all-MiniLM-L6-v2"
    vector_store: str = "chromadb"
    db_path: str = "~/.neopilot/memory/"
    max_context_tokens: int = 8000


class LibreOfficeSettings(BaseModel):
    connection: str = "socket"
    host: str = "localhost"
    port: int = 2002
    auto_start: bool = True
    timeout_seconds: int = 15


class AgentSettings(BaseModel):
    mode: AgentMode = AgentMode.AUTONOMOUS
    language: str = "pt-BR"
    confirmation_timeout_seconds: int = 60
    max_steps_per_task: int = 50
    max_retries_per_step: int = 3
    step_timeout_seconds: int = 30


class LoggingSettings(BaseModel):
    level: str = "INFO"
    file: str = "~/.neopilot/logs/neopilot.log"
    max_bytes: int = 10_485_760
    backup_count: int = 5
    format: str = "json"


# ─── Root Settings ─────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEOPILOT_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    agent: AgentSettings = AgentSettings()
    llm: LLMSettings = LLMSettings()
    voice: VoiceSettings = VoiceSettings()
    security: SecuritySettings = SecuritySettings()
    memory: MemorySettings = MemorySettings()
    libreoffice: LibreOfficeSettings = LibreOfficeSettings()
    logging: LoggingSettings = LoggingSettings()

    # API keys (from env or vault)
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(default=None, alias="ELEVENLABS_API_KEY")

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "Settings":
        """Load settings from YAML file, overridden by env vars.
        Env vars always win over YAML values (pydantic-settings priority).
        """
        import os as _os
        path = Path(yaml_path).expanduser()
        if not path.exists():
            return cls()

        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        # Env vars take precedence: remove YAML keys that have env override
        prefix = "NEOPILOT_"
        delim = "__"

        def _has_env_override(keys: list[str]) -> bool:
            env_key = prefix + delim.join(k.upper() for k in keys)
            return _os.environ.get(env_key) is not None

        def _filter_yaml(d: dict, path: list[str]) -> dict:
            result = {}
            for k, v in d.items():
                current_path = path + [k]
                if _has_env_override(current_path):
                    continue  # env var wins
                if isinstance(v, dict):
                    filtered = _filter_yaml(v, current_path)
                    if filtered:
                        result[k] = filtered
                else:
                    result[k] = v
            return result

        filtered = _filter_yaml(data, [])
        return cls(**filtered)

    def get_neopilot_dir(self) -> Path:
        d = Path("~/.neopilot").expanduser()
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_memory_path(self) -> Path:
        p = Path(self.memory.db_path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_log_path(self) -> Path:
        p = Path(self.logging.file).expanduser().parent
        p.mkdir(parents=True, exist_ok=True)
        return Path(self.logging.file).expanduser()


# ─── Singleton ────────────────────────────────────────────────────────────────

_settings: Optional[Settings] = None
_CONFIG_PATH = Path("~/.neopilot/config.yaml").expanduser()
_DEFAULT_CONFIG = Path(__file__).parent.parent.parent.parent.parent / "config" / "default.yaml"


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        # Prefer user config, fall back to default
        if _CONFIG_PATH.exists():
            _settings = Settings.from_yaml(_CONFIG_PATH)
        elif _DEFAULT_CONFIG.exists():
            _settings = Settings.from_yaml(_DEFAULT_CONFIG)
        else:
            _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    global _settings
    _settings = None
    return get_settings()


# Convenience alias
settings = get_settings()
