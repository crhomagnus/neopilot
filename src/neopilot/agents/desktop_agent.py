"""
NeoPilot Desktop Agent
Controle de apps desktop via AT-SPI (dogtail/pyatspi) + xdotool/ydotool.
Inclui Modo Professor: detecção e correção de erros em tempo real.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from neopilot.agents.input_controller import InputController
from neopilot.core.logger import get_logger
from neopilot.perception.accessibility import AccessibilityTree, AccessibleElement
from neopilot.perception.context_builder import ContextBuilder

logger = get_logger("desktop_agent")


class ErrorSeverity(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    CRITICAL = "critical"


@dataclass
class UserError:
    severity: ErrorSeverity
    description: str
    expected_action: str
    actual_action: str
    correction: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class DesktopAction:
    action_type: str  # click|type|hotkey|focus|scroll|drag
    app_name: Optional[str] = None
    element_role: Optional[str] = None
    element_name: Optional[str] = None
    text: Optional[str] = None
    key: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    from_x: Optional[int] = None
    from_y: Optional[int] = None


@dataclass
class DesktopResult:
    success: bool
    method: str  # "atspi" | "xdotool" | "visual"
    data: Any = None
    error: Optional[str] = None


class ProfessorMode:
    """
    Modo Professor: observa ações do usuário e detecta desvios do plano.
    """

    def __init__(self, on_error_callback: Callable[[UserError], None]):
        self.active = False
        self.expected_steps: list[dict] = []
        self.current_step_index = 0
        self.errors_detected: list[UserError] = []
        self._on_error = on_error_callback
        self._last_state: Optional[dict] = None

    def start(self, task_steps: list[dict]) -> None:
        """Inicia monitoramento com lista de passos esperados."""
        self.expected_steps = task_steps
        self.current_step_index = 0
        self.errors_detected = []
        self.active = True
        logger.info(
            "Modo Professor ativado",
            total_steps=len(task_steps)
        )

    def stop(self) -> None:
        self.active = False
        logger.info(
            "Modo Professor desativado",
            errors_detected=len(self.errors_detected)
        )

    def observe_action(
        self,
        actual_action: dict,
        current_state: dict,
    ) -> Optional[UserError]:
        """
        Compara ação atual do usuário com o passo esperado.
        Retorna UserError se houver desvio.
        """
        if not self.active or self.current_step_index >= len(self.expected_steps):
            return None

        expected = self.expected_steps[self.current_step_index]
        expected_type = expected.get("action_type")
        expected_target = expected.get("target", "")
        actual_type = actual_action.get("action_type")
        actual_target = actual_action.get("target", "")

        # Verifica se ação bate com o esperado
        is_correct = (
            expected_type == actual_type
            and (not expected_target or expected_target.lower() in actual_target.lower())
        )

        if is_correct:
            self.current_step_index += 1
            logger.debug("Passo correto", step=self.current_step_index)
            return None

        # Determina severidade do erro
        severity = self._classify_error(expected, actual_action)
        error = UserError(
            severity=severity,
            description=f"Esperado: {expected_type} em '{expected_target}', "
                        f"mas foi: {actual_type} em '{actual_target}'",
            expected_action=str(expected),
            actual_action=str(actual_action),
            correction=expected.get("correction_hint"),
        )

        self.errors_detected.append(error)
        self._on_error(error)
        logger.warning(
            "Erro detectado pelo Professor",
            severity=severity.value,
            description=error.description,
        )
        return error

    def _classify_error(self, expected: dict, actual: dict) -> ErrorSeverity:
        """Classifica severidade do erro."""
        # Erros que podem causar perda de dados = crítico
        critical_actions = {"delete_file", "submit_form", "send_email", "overwrite"}
        if actual.get("action_type") in critical_actions:
            return ErrorSeverity.CRITICAL
        # Ação completamente errada = moderado
        if expected.get("action_type") != actual.get("action_type"):
            return ErrorSeverity.MODERATE
        # Alvo errado mas ação certa = leve
        return ErrorSeverity.LIGHT

    def advance_step(self) -> None:
        """Avança manualmente para o próximo passo (após correção)."""
        if self.current_step_index < len(self.expected_steps):
            self.current_step_index += 1

    def get_progress(self) -> dict:
        return {
            "current_step": self.current_step_index,
            "total_steps": len(self.expected_steps),
            "errors": len(self.errors_detected),
            "completion_pct": (
                self.current_step_index / max(len(self.expected_steps), 1) * 100
            ),
        }

    def generate_session_report(self) -> dict:
        """Gera relatório completo da sessão de aprendizagem."""
        return {
            "total_steps": len(self.expected_steps),
            "completed_steps": self.current_step_index,
            "completion_pct": self.get_progress()["completion_pct"],
            "total_errors": len(self.errors_detected),
            "errors_by_severity": {
                "light": sum(1 for e in self.errors_detected if e.severity == ErrorSeverity.LIGHT),
                "moderate": sum(1 for e in self.errors_detected if e.severity == ErrorSeverity.MODERATE),
                "critical": sum(1 for e in self.errors_detected if e.severity == ErrorSeverity.CRITICAL),
            },
            "errors_detail": [
                {
                    "timestamp": e.timestamp,
                    "severity": e.severity.value,
                    "description": e.description,
                }
                for e in self.errors_detected
            ],
        }


class DesktopAgent:
    """
    Agente especialista em controle de apps desktop Linux.
    Usa AT-SPI como método primário e input sintético como fallback.
    """

    def __init__(self):
        self.input = InputController()
        self.accessibility = AccessibilityTree()
        self.context_builder = ContextBuilder()
        self.professor = ProfessorMode(on_error_callback=self._handle_professor_error)
        self._error_callbacks: list[Callable] = []

    def on_error_detected(self, callback: Callable[[UserError], None]) -> None:
        """Registra callback para quando erro é detectado."""
        self._error_callbacks.append(callback)

    def _handle_professor_error(self, error: UserError) -> None:
        for cb in self._error_callbacks:
            try:
                cb(error)
            except Exception as e:
                logger.error("Erro no callback de professor", error=str(e))

    async def execute_action(self, action: DesktopAction) -> DesktopResult:
        """Executa ação desktop com fallback automático."""
        # Tenta AT-SPI primeiro (mais semântico e confiável)
        result = await self._try_atspi(action)
        if result.success:
            return result

        # Fallback para input sintético (xdotool/ydotool)
        logger.debug("AT-SPI falhou, usando input sintético", action=action.action_type)
        return await self._try_synthetic_input(action)

    async def _try_atspi(self, action: DesktopAction) -> DesktopResult:
        """Tenta executar via AT-SPI."""
        if not self.accessibility._pyatspi_available:
            return DesktopResult(success=False, method="atspi", error="pyatspi não disponível")

        try:
            app = None
            if action.app_name:
                app = self.accessibility.get_application(action.app_name)
                if not app:
                    return DesktopResult(
                        success=False, method="atspi",
                        error=f"App '{action.app_name}' não encontrado"
                    )

            if action.action_type == "click" and action.element_name:
                node = self.accessibility.find_element(
                    app or self._get_desktop(),
                    role=action.element_role,
                    name=action.element_name,
                )
                if node:
                    success = self.accessibility.perform_action(node, "click")
                    return DesktopResult(
                        success=success, method="atspi",
                        error=None if success else "Ação click falhou"
                    )

            elif action.action_type == "type" and action.text:
                node = self.accessibility.find_element(
                    app or self._get_desktop(),
                    role="text",
                )
                if node:
                    success = self.accessibility.set_text(node, action.text)
                    return DesktopResult(success=success, method="atspi")

            elif action.action_type == "focus" and action.element_name:
                node = self.accessibility.find_element(
                    app or self._get_desktop(),
                    name=action.element_name,
                )
                if node:
                    success = self.accessibility.perform_action(node, "focus")
                    return DesktopResult(success=success, method="atspi")

        except Exception as e:
            logger.debug("AT-SPI falhou", error=str(e))

        return DesktopResult(success=False, method="atspi", error="Elemento não encontrado")

    async def _try_synthetic_input(self, action: DesktopAction) -> DesktopResult:
        """Executa ação via input sintético (xdotool/ydotool)."""
        try:
            if action.action_type == "click":
                if action.x is not None and action.y is not None:
                    self.input.click(action.x, action.y)
                    return DesktopResult(success=True, method="xdotool")

            elif action.action_type == "type" and action.text:
                self.input.type_text(action.text)
                return DesktopResult(success=True, method="xdotool")

            elif action.action_type == "hotkey" and action.key:
                self.input.press_key(action.key)
                return DesktopResult(success=True, method="xdotool")

            elif action.action_type == "drag":
                if all(v is not None for v in [action.from_x, action.from_y, action.x, action.y]):
                    self.input.drag(action.from_x, action.from_y, action.x, action.y)
                    return DesktopResult(success=True, method="xdotool")

        except Exception as e:
            logger.error("Input sintético falhou", error=str(e))
            return DesktopResult(success=False, method="xdotool", error=str(e))

        return DesktopResult(success=False, method="xdotool", error="Ação não suportada")

    def _get_desktop(self) -> Any:
        return self.accessibility.get_desktop()

    def get_active_application(self) -> Optional[str]:
        """Retorna nome do aplicativo em foco."""
        try:
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            return result.stdout.strip()
        except Exception:
            return None

    async def observe_and_react(self, expected_action: dict) -> Optional[UserError]:
        """
        Captura estado atual e compara com ação esperada (modo professor).
        """
        current_state = self.context_builder.build(
            capture_a11y=True, run_ocr=False
        )
        actual_action = {
            "action_type": "unknown",
            "target": current_state.active_window.get("name", ""),
        }
        return self.professor.observe_action(actual_action, current_state.__dict__)

    def list_open_applications(self) -> list[str]:
        return self.accessibility.list_applications()
