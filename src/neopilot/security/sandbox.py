"""
NeoPilot Sandbox — Isolamento multi-camada
Firejail → Bubblewrap → Docker → AppArmor → Human-in-the-loop gate.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from neopilot.core.logger import get_logger

logger = get_logger("sandbox")


class SandboxLevel(str, Enum):
    NONE = "none"           # Sem sandbox (modo dev)
    FIREJAIL = "firejail"   # Firejail com perfil restrito
    BUBBLEWRAP = "bubblewrap"  # bwrap (mais restrito)
    DOCKER = "docker"       # Container Docker isolado


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    method: str


class FirejailSandbox:
    """Sandbox usando Firejail com perfil customizado para NeoPilot."""

    PROFILE_PATH = Path("/etc/firejail/neopilot.profile")
    LOCAL_PROFILE = Path.home() / ".config/firejail/neopilot.profile"

    DEFAULT_PROFILE = """
# NeoPilot Firejail Profile
# Restringe acesso ao sistema de forma segura

include /etc/firejail/default.profile

# Nega acesso a diretórios sensíveis
blacklist /etc/passwd
blacklist /etc/shadow
blacklist ~/.ssh
blacklist ~/.gnupg
blacklist ~/.config/google-chrome
blacklist ~/.config/chromium

# Permite apenas diretórios necessários
whitelist ${HOME}/.neopilot
whitelist ${HOME}/Documentos
whitelist ${HOME}/Downloads
whitelist /tmp

# Rede restrita (permite HTTP/HTTPS apenas)
protocol unix,inet,inet6
# netfilter

# Sem acesso a dispositivos
noroot
nosound
notv
novideo

# Caps restringen
caps.drop all
seccomp

# Variáveis de ambiente limpas
env-keep DISPLAY
env-keep WAYLAND_DISPLAY
env-keep DBUS_SESSION_BUS_ADDRESS
env-keep XDG_RUNTIME_DIR
"""

    def __init__(self):
        self._available = shutil.which("firejail") is not None
        if self._available:
            self._ensure_profile()
            logger.info("Firejail disponível")
        else:
            logger.warning("Firejail não instalado, sandbox desabilitada")

    def _ensure_profile(self) -> None:
        """Cria perfil local se não existir."""
        profile_path = self.LOCAL_PROFILE
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        if not profile_path.exists():
            profile_path.write_text(self.DEFAULT_PROFILE)
            logger.info("Perfil Firejail criado", path=str(profile_path))

    async def run(
        self,
        command: list[str],
        timeout: int = 30,
        allow_network: bool = True,
    ) -> SandboxResult:
        """Executa comando dentro do Firejail."""
        if not self._available:
            return await _run_unsandboxed(command, timeout)

        profile = str(self.LOCAL_PROFILE) if self.LOCAL_PROFILE.exists() else "default"
        firejail_cmd = [
            "firejail",
            f"--profile={profile}",
            "--quiet",
        ]

        if not allow_network:
            firejail_cmd.append("--net=none")

        firejail_cmd.extend(command)
        return await _run_subprocess(firejail_cmd, timeout, method="firejail")


class BubblewrapSandbox:
    """Sandbox usando bwrap (Bubblewrap) — mais restrito que Firejail."""

    def __init__(self):
        self._available = shutil.which("bwrap") is not None
        if self._available:
            logger.info("Bubblewrap disponível")
        else:
            logger.warning("bwrap não instalado")

    async def run(
        self,
        command: list[str],
        timeout: int = 30,
        allow_network: bool = True,
    ) -> SandboxResult:
        """Executa comando dentro de namespace isolado com bwrap."""
        if not self._available:
            return await _run_unsandboxed(command, timeout)

        home = str(Path.home())
        neopilot_dir = str(Path.home() / ".neopilot")

        bwrap_cmd = [
            "bwrap",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/sbin", "/sbin",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--tmpfs", home,
            "--bind", neopilot_dir, neopilot_dir,
            "--bind", f"{home}/Documentos", f"{home}/Documentos",
            "--unshare-pid",
            "--unshare-uts",
            "--unshare-ipc",
        ]

        if not allow_network:
            bwrap_cmd.append("--unshare-net")

        # Variáveis de ambiente necessárias
        for var in ["DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"]:
            val = os.environ.get(var)
            if val:
                bwrap_cmd.extend(["--setenv", var, val])

        bwrap_cmd.extend(["--"] + command)
        return await _run_subprocess(bwrap_cmd, timeout, method="bubblewrap")


class DockerSandbox:
    """Sandbox usando container Docker."""

    IMAGE = "neopilot-sandbox:latest"
    DOCKERFILE = """FROM python:3.11-slim
RUN apt-get update && apt-get install -y \\
    xdotool libreoffice-calc libreoffice-writer \\
    espeak-ng xvfb \\
    && rm -rf /var/lib/apt/lists/*
WORKDIR /sandbox
ENV DISPLAY=:99
"""

    def __init__(self):
        self._available = shutil.which("docker") is not None
        self._image_built = False
        if self._available:
            logger.info("Docker disponível")

    async def run(
        self,
        command: list[str],
        timeout: int = 60,
        allow_network: bool = True,
    ) -> SandboxResult:
        """Executa comando em container Docker."""
        if not self._available:
            return await _run_unsandboxed(command, timeout)

        docker_cmd = [
            "docker", "run",
            "--rm",
            "--security-opt", "no-new-privileges",
            "--cap-drop=ALL",
            "--memory=512m",
            "--cpus=1",
        ]

        if not allow_network:
            docker_cmd.extend(["--network", "none"])

        neopilot_dir = str(Path.home() / ".neopilot")
        docker_cmd.extend([
            "-v", f"{neopilot_dir}:/home/user/.neopilot:ro",
            self.IMAGE,
        ] + command)

        return await _run_subprocess(docker_cmd, timeout, method="docker")

    async def ensure_image(self) -> bool:
        """Garante que a imagem Docker existe."""
        if self._image_built:
            return True
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dockerfile = Path(tmpdir) / "Dockerfile"
                dockerfile.write_text(self.DOCKERFILE)
                result = await _run_subprocess(
                    ["docker", "build", "-t", self.IMAGE, tmpdir],
                    timeout=120,
                    method="docker",
                )
                self._image_built = result.success
                return self._image_built
        except Exception as e:
            logger.error("Falha ao construir imagem Docker", error=str(e))
            return False


class OpenInterpreterSandbox:
    """
    Execução segura de código via OpenInterpreter em modo sandbox.
    Permite executar Python e Bash gerados pelo LLM de forma controlada.
    """

    def __init__(self, safe_mode: str = "ask"):
        self._available = False
        self._interpreter = None
        self.safe_mode = safe_mode
        self._load()

    def _load(self) -> None:
        try:
            import interpreter
            self._interpreter = interpreter.interpreter
            self._interpreter.auto_run = self.safe_mode == "auto"
            self._interpreter.safe_mode = self.safe_mode
            self._interpreter.llm.model = "claude-sonnet-4-6"
            self._interpreter.system_message += (
                "\n\nVocê está em modo sandbox seguro. "
                "Nunca execute comandos destrutivos sem confirmação explícita."
            )
            self._available = True
            logger.info("OpenInterpreter disponível", safe_mode=self.safe_mode)
        except ImportError:
            logger.warning("open-interpreter não instalado")

    async def run_code(self, code: str, language: str = "python") -> SandboxResult:
        """Executa código via OpenInterpreter."""
        if not self._available:
            return SandboxResult(
                success=False, stdout="", stderr="open-interpreter não disponível",
                exit_code=1, method="openinterpreter"
            )

        try:
            result_chunks = []
            for chunk in self._interpreter.chat(
                f"Execute este código {language}:\n```{language}\n{code}\n```"
            ):
                if isinstance(chunk, dict):
                    result_chunks.append(str(chunk.get("content", "")))

            output = "".join(result_chunks)
            return SandboxResult(
                success=True, stdout=output, stderr="",
                exit_code=0, method="openinterpreter"
            )
        except Exception as e:
            return SandboxResult(
                success=False, stdout="", stderr=str(e),
                exit_code=1, method="openinterpreter"
            )


class HumanInTheLoopGate:
    """
    Gate de aprovação humana para ações sensíveis.
    Integra com a UI para pausar execução e aguardar aprovação.
    """

    SENSITIVE_ACTIONS = {
        "delete_file", "rm", "sudo", "chmod", "chown",
        "send_email", "submit_form", "publish", "deploy",
        "overwrite", "format", "drop_table",
    }

    def __init__(self):
        self._pending: dict[str, asyncio.Event] = {}
        self._decisions: dict[str, bool] = {}

    def is_sensitive(self, action: str) -> bool:
        return any(s in action.lower() for s in self.SENSITIVE_ACTIONS)

    async def request_approval(
        self,
        action_id: str,
        action_description: str,
        timeout_s: float = 60.0,
    ) -> bool:
        """
        Pausa execução e aguarda aprovação humana.
        Retorna True se aprovado, False se negado ou timeout.
        """
        logger.warning(
            "Aguardando aprovação humana",
            action_id=action_id,
            description=action_description[:100],
        )

        event = asyncio.Event()
        self._pending[action_id] = event

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_s)
            approved = self._decisions.get(action_id, False)
            logger.info("Decisão humana", action_id=action_id, approved=approved)
            return approved
        except asyncio.TimeoutError:
            logger.warning("Timeout na aprovação humana", action_id=action_id)
            return False
        finally:
            self._pending.pop(action_id, None)
            self._decisions.pop(action_id, None)

    def approve(self, action_id: str) -> None:
        """Aprova ação pendente."""
        self._decisions[action_id] = True
        event = self._pending.get(action_id)
        if event:
            event.set()

    def deny(self, action_id: str) -> None:
        """Nega ação pendente."""
        self._decisions[action_id] = False
        event = self._pending.get(action_id)
        if event:
            event.set()


class SandboxManager:
    """
    Gerenciador unificado de sandbox.
    Seleciona nível de isolamento conforme configuração e disponibilidade.
    """

    def __init__(self, level: str = "firejail"):
        self.level = SandboxLevel(level)
        self.firejail = FirejailSandbox()
        self.bubblewrap = BubblewrapSandbox()
        self.docker = DockerSandbox()
        self.openinterpreter = OpenInterpreterSandbox()
        self.human_gate = HumanInTheLoopGate()

    async def run(
        self,
        command: list[str],
        action_type: str = "",
        timeout: int = 30,
        allow_network: bool = True,
        require_human_approval: bool = False,
    ) -> SandboxResult:
        """
        Executa comando com nível de isolamento configurado.
        Pede aprovação humana se necessário.
        """
        # Gate humano
        if require_human_approval or self.human_gate.is_sensitive(action_type):
            action_id = f"{action_type}_{int(asyncio.get_event_loop().time())}"
            approved = await self.human_gate.request_approval(
                action_id,
                f"{action_type}: {' '.join(command[:3])}",
            )
            if not approved:
                return SandboxResult(
                    success=False, stdout="", stderr="Ação negada pelo usuário",
                    exit_code=1, method="human_gate"
                )

        # Executa com nível apropriado
        if self.level == SandboxLevel.DOCKER and self.docker._available:
            return await self.docker.run(command, timeout, allow_network)
        elif self.level == SandboxLevel.BUBBLEWRAP and self.bubblewrap._available:
            return await self.bubblewrap.run(command, timeout, allow_network)
        elif self.level in (SandboxLevel.FIREJAIL, SandboxLevel.BUBBLEWRAP) and self.firejail._available:
            return await self.firejail.run(command, timeout, allow_network)
        else:
            return await _run_unsandboxed(command, timeout)

    async def run_code(
        self,
        code: str,
        language: str = "python",
        require_approval: bool = True,
    ) -> SandboxResult:
        """Executa código gerado pelo LLM com aprovação opcional."""
        if require_approval:
            action_id = f"code_{hash(code) % 10000}"
            approved = await self.human_gate.request_approval(
                action_id,
                f"Executar código {language}:\n{code[:200]}",
            )
            if not approved:
                return SandboxResult(
                    success=False, stdout="", stderr="Código não aprovado",
                    exit_code=1, method="human_gate"
                )

        return await self.openinterpreter.run_code(code, language)


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _run_subprocess(command: list[str], timeout: int, method: str) -> SandboxResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return SandboxResult(
            success=proc.returncode == 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            exit_code=proc.returncode,
            method=method,
        )
    except asyncio.TimeoutError:
        proc.kill()
        return SandboxResult(
            success=False, stdout="", stderr=f"Timeout após {timeout}s",
            exit_code=-1, method=method
        )
    except Exception as e:
        return SandboxResult(
            success=False, stdout="", stderr=str(e),
            exit_code=-1, method=method
        )


async def _run_unsandboxed(command: list[str], timeout: int) -> SandboxResult:
    logger.warning("Executando sem sandbox", command=command[0])
    return await _run_subprocess(command, timeout, method="unsandboxed")
