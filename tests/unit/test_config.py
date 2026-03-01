"""Testes unitários — Config e Settings."""

import pytest
from pathlib import Path

from neopilot.core.config import (
    AgentSettings, AgentMode, LLMSettings, LLMConfig, LLMProvider,
    SecuritySettings, VoiceSettings, STTConfig, TTSConfig, get_settings,
)


def test_default_agent_settings():
    s = AgentSettings()
    assert s.mode == AgentMode.AUTONOMOUS
    assert s.max_steps_per_task == 50


def test_default_llm_settings():
    s = LLMSettings()
    assert s.primary.provider == LLMProvider.ANTHROPIC
    assert s.primary.temperature == 0.1
    assert s.primary.model == "claude-sonnet-4-6"


def test_security_is_path_allowed():
    s = SecuritySettings()
    # Paths dentro de home/Documents são permitidos
    home = Path.home()
    allowed_path = str(home / "Documents" / "file.txt")
    blocked_ssh = str(home / ".ssh" / "id_rsa")

    assert s.is_path_allowed(allowed_path)
    assert not s.is_path_allowed(blocked_ssh)


def test_security_is_path_blocked_by_default():
    s = SecuritySettings()
    home = Path.home()
    gnupg_path = str(home / ".gnupg" / "pubring.kbx")
    assert not s.is_path_allowed(gnupg_path)


def test_security_requires_confirmation():
    s = SecuritySettings()
    assert s.requires_confirmation("delete_file")
    assert s.requires_confirmation("send_email")
    assert s.requires_confirmation("form_submit")
    assert s.requires_confirmation("execute_script")
    assert not s.requires_confirmation("read_file")
    assert not s.requires_confirmation("click")
    assert not s.requires_confirmation("navigate")


def test_get_settings_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_env_override(monkeypatch):
    """Testa override via variável de ambiente."""
    monkeypatch.setenv("NEOPILOT_AGENT__MODE", "autonomous")

    # Força recriação do singleton
    import neopilot.core.config as conf_module
    conf_module._settings = None

    try:
        s = get_settings()
        assert s.agent.mode == AgentMode.AUTONOMOUS
    finally:
        conf_module._settings = None


def test_voice_settings_defaults():
    s = VoiceSettings()
    assert s.stt.language == "pt"
    assert s.hotkey == "ctrl+space"
    assert s.push_to_talk_key == "ctrl+shift+space"


def test_llm_config_validation():
    cfg = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o", temperature=0.5)
    assert cfg.provider == LLMProvider.OPENAI
    assert cfg.temperature == 0.5


def test_security_allowed_directories_default():
    s = SecuritySettings()
    assert "~/Documents" in s.allowed_directories
    assert "~/Downloads" in s.allowed_directories


def test_security_blocked_directories_default():
    s = SecuritySettings()
    assert "~/.ssh" in s.blocked_directories
    assert "~/.gnupg" in s.blocked_directories
