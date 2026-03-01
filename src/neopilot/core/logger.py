"""
NeoPilot Structured Logger
Baseado em structlog com output JSON para arquivo e console legível.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger


def _add_severity(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Adiciona campo 'severity' compatível com GCP/Datadog."""
    event_dict["severity"] = method_name.upper()
    return event_dict


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    json_format: bool = True,
) -> None:
    """Configura structlog + stdlib logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _add_severity,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Console renderer (human-friendly)
    console_renderer = structlog.dev.ConsoleRenderer(colors=True)

    # File renderer (JSON)
    file_renderer = structlog.processors.JSONRenderer()

    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # File handler (rotating)
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Root logger config
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
    )

    # Silence noisy libraries
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure ProcessorFormatter for each handler
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=file_renderer if json_format else console_renderer,
        foreign_pre_chain=shared_processors,
    )
    for handler in handlers:
        handler.setFormatter(formatter)


def get_logger(name: str = "neopilot") -> structlog.BoundLogger:
    return structlog.get_logger(name)


# ─── Action Audit Logger ──────────────────────────────────────────────────────

class AuditLogger:
    """Log imutável (append-only) de todas as ações do agente."""

    def __init__(self, audit_path: str | Path):
        self.path = Path(audit_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger("audit")

    def log_action(
        self,
        action_type: str,
        details: dict[str, Any],
        session_id: str,
        approved: bool = True,
        result: str | None = None,
    ) -> None:
        import hashlib
        import json
        import time

        entry = {
            "timestamp": time.time(),
            "session_id": session_id,
            "action_type": action_type,
            "approved": approved,
            "result": result,
            **details,
        }

        # Append-only write com hash da linha anterior para integridade
        line = json.dumps(entry, ensure_ascii=False)
        if self.path.exists():
            prev = self.path.read_bytes()
            entry["prev_hash"] = hashlib.sha256(prev).hexdigest()
            line = json.dumps(entry, ensure_ascii=False)

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        self._logger.info(
            "action_logged",
            action_type=action_type,
            approved=approved,
            session_id=session_id,
        )
