"""
NeoPilot Accessibility Layer
Leitura da árvore AT-SPI para apps GTK/GNOME via pyatspi.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from neopilot.core.logger import get_logger

logger = get_logger("accessibility")


@dataclass
class AccessibleElement:
    role: str
    name: str
    description: str
    bounds: dict[str, int]        # x, y, width, height
    states: list[str]
    attributes: dict[str, str]
    children: list["AccessibleElement"] = field(default_factory=list)
    action_names: list[str] = field(default_factory=list)
    text: Optional[str] = None
    value: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "role": self.role,
            "name": self.name,
            "description": self.description,
            "bounds": self.bounds,
            "states": self.states,
            "text": self.text,
            "value": self.value,
            "actions": self.action_names,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    def is_visible(self) -> bool:
        return "showing" in self.states and "visible" in self.states

    def is_enabled(self) -> bool:
        return "enabled" in self.states

    def is_focused(self) -> bool:
        return "focused" in self.states

    def center(self) -> tuple[int, int]:
        x = self.bounds["x"] + self.bounds["width"] // 2
        y = self.bounds["y"] + self.bounds["height"] // 2
        return x, y


class AccessibilityTree:
    """Interface com a árvore de acessibilidade AT-SPI."""

    def __init__(self):
        self._pyatspi_available = self._check_pyatspi()

    def _check_pyatspi(self) -> bool:
        try:
            import pyatspi  # noqa: F401
            # Verifica se o daemon AT-SPI está ativo tentando chamar getDesktop
            pyatspi.getDesktop(0)
            return True
        except ImportError:
            logger.warning("pyatspi não disponível — acessibilidade semântica desativada")
            return False
        except Exception:
            # AT-SPI daemon não está rodando (normal em sessão sem GUI/acessibilidade)
            logger.debug("AT-SPI daemon não disponível — usando fallback de input sintético")
            return False

    def get_desktop(self) -> Optional[Any]:
        if not self._pyatspi_available:
            return None
        try:
            import pyatspi
            return pyatspi.getDesktop(0)
        except Exception:
            return None

    def get_application(self, app_name: str) -> Optional[Any]:
        """Localiza aplicativo pelo nome na árvore AT-SPI."""
        if not self._pyatspi_available:
            return None
        try:
            import pyatspi
            desktop = pyatspi.getDesktop(0)
            for app in desktop:
                if app and app.name and app_name.lower() in app.name.lower():
                    return app
        except Exception:
            pass
        return None

    def list_applications(self) -> list[str]:
        """Lista todos os aplicativos acessíveis."""
        if not self._pyatspi_available:
            return []
        try:
            import pyatspi
            desktop = pyatspi.getDesktop(0)
            return [app.name for app in desktop if app and app.name]
        except Exception:
            return []

    def build_tree(
        self, node: Any, max_depth: int = 5, current_depth: int = 0
    ) -> Optional[AccessibleElement]:
        """Constrói árvore de elementos acessíveis recursivamente."""
        if not self._pyatspi_available or node is None:
            return None
        if current_depth > max_depth:
            return None

        try:
            import pyatspi

            role = node.getLocalizedRoleName() or ""
            name = node.name or ""
            description = node.description or ""

            # Bounds
            try:
                bounds_obj = node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
                bounds = {
                    "x": bounds_obj.x,
                    "y": bounds_obj.y,
                    "width": bounds_obj.width,
                    "height": bounds_obj.height,
                }
            except Exception:
                bounds = {"x": 0, "y": 0, "width": 0, "height": 0}

            # States
            state_set = node.getState()
            states = [
                s.value_nick for s in pyatspi.StateType
                if state_set.contains(s)
            ]

            # Attributes
            try:
                attrs = dict(node.getAttributes())
            except Exception:
                attrs = {}

            # Actions
            action_names = []
            try:
                action_iface = node.queryAction()
                action_names = [
                    action_iface.getName(i)
                    for i in range(action_iface.nActions)
                ]
            except Exception:
                pass

            # Text
            text_content = None
            try:
                text_iface = node.queryText()
                text_content = text_iface.getText(0, -1)
            except Exception:
                pass

            # Value
            value_content = None
            try:
                value_iface = node.queryValue()
                value_content = value_iface.currentValue
            except Exception:
                pass

            # Children
            children = []
            if current_depth < max_depth:
                for child in node:
                    child_elem = self.build_tree(
                        child, max_depth, current_depth + 1
                    )
                    if child_elem:
                        children.append(child_elem)

            return AccessibleElement(
                role=role,
                name=name,
                description=description,
                bounds=bounds,
                states=states,
                attributes=attrs,
                children=children,
                action_names=action_names,
                text=text_content,
                value=value_content,
            )

        except Exception as e:
            logger.debug("Erro ao processar nó AT-SPI", error=str(e))
            return None

    def find_element(
        self,
        root: Any,
        role: Optional[str] = None,
        name: Optional[str] = None,
        partial_name: bool = False,
    ) -> Optional[Any]:
        """Busca elemento na árvore por role e/ou nome."""
        if not self._pyatspi_available or root is None:
            return None

        try:
            root_role = root.getLocalizedRoleName() or ""
            root_name = root.name or ""

            role_match = role is None or role.lower() in root_role.lower()
            if name is None:
                name_match = True
            elif partial_name:
                name_match = name.lower() in root_name.lower()
            else:
                name_match = name.lower() == root_name.lower()

            if role_match and name_match and (role or name):
                return root

            for child in root:
                result = self.find_element(child, role, name, partial_name)
                if result:
                    return result

        except Exception:
            pass

        return None

    def perform_action(self, node: Any, action_name: str = "click") -> bool:
        """Executa ação de acessibilidade em um elemento."""
        if not self._pyatspi_available or node is None:
            return False
        try:
            action_iface = node.queryAction()
            for i in range(action_iface.nActions):
                if action_iface.getName(i).lower() == action_name.lower():
                    action_iface.doAction(i)
                    return True
            return False
        except Exception as e:
            logger.error("Falha ao executar ação AT-SPI", error=str(e))
            return False

    def set_text(self, node: Any, text: str) -> bool:
        """Define texto em um campo de entrada."""
        if not self._pyatspi_available or node is None:
            return False
        try:
            edit_iface = node.queryEditableText()
            edit_iface.setTextContents(text)
            return True
        except Exception as e:
            logger.error("Falha ao definir texto AT-SPI", error=str(e))
            return False

    def watch_events(
        self,
        callback: Callable[[str, Any], None],
        event_types: Optional[list[str]] = None,
    ) -> None:
        """Monitora eventos de acessibilidade em thread separada."""
        if not self._pyatspi_available:
            return

        import pyatspi

        default_events = [
            "object:state-changed:focused",
            "object:text-changed:insert",
            "window:activate",
            "window:deactivate",
        ]
        events = event_types or default_events

        def listener(event: Any) -> None:
            try:
                callback(event.type, event.source)
            except Exception as e:
                logger.debug("Erro em AT-SPI event listener", error=str(e))

        def run() -> None:
            for event_type in events:
                pyatspi.Registry.registerEventListener(listener, event_type)
            pyatspi.Registry.start()

        thread = threading.Thread(target=run, daemon=True, name="at-spi-watcher")
        thread.start()
        logger.info("AT-SPI event watcher iniciado", events=events)
