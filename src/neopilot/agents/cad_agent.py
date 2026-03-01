"""
NeoPilot CAD/Wine Agent
Controle de aplicativos Windows via Wine usando PyAutoGUI + SikuliX.
Suporte a: Fusion 360, Rhino3D, CorelDRAW, AutoCAD.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from neopilot.agents.input_controller import InputController
from neopilot.core.logger import get_logger
from neopilot.perception.visual_grounder import VisualGrounder

logger = get_logger("cad_agent")


@dataclass
class CADAction:
    action_type: str  # click|type|hotkey|tool_select|template|macro
    target: Optional[str] = None      # Nome do elemento/botão
    text: Optional[str] = None
    key: Optional[str] = None
    tool_name: Optional[str] = None   # Nome da ferramenta CAD
    template_path: Optional[str] = None  # Template SikuliX para matching
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass
class CADResult:
    success: bool
    method: str  # "sikulix" | "pyautogui" | "wine_cli"
    data: Any = None
    error: Optional[str] = None


# Atalhos comuns para CADs populares
CAD_HOTKEYS = {
    "fusion360": {
        "save": "ctrl+s",
        "undo": "ctrl+z",
        "extrude": "e",
        "sketch": "s",
        "new_component": "alt+ctrl+n",
        "render": "r",
        "top_view": "7",
        "isometric": "ctrl+0",
    },
    "rhino3d": {
        "save": "ctrl+s",
        "undo": "ctrl+z",
        "line": "l",
        "polyline": "pl",
        "circle": "c",
        "extrude_curve": "extrude",
        "render": "render",
        "top": "t",
    },
    "coreldraw": {
        "save": "ctrl+s",
        "undo": "ctrl+z",
        "text_tool": "t",
        "pick_tool": "f1",
        "zoom_in": "f2",
        "zoom_out": "f3",
        "export": "ctrl+e",
    },
    "autocad": {
        "save": "ctrl+s",
        "undo": "ctrl+z",
        "line": "l\n",
        "circle": "c\n",
        "move": "m\n",
        "zoom_extents": "z\ne\n",
    },
}


class SikuliXBridge:
    """
    Ponte para SikuliX — template matching visual para apps GUI.
    Funciona mesmo sem acessibilidade AT-SPI.
    """

    def __init__(self, sikulix_jar: Optional[str] = None):
        self._jar = sikulix_jar or self._find_sikulix()
        self._available = self._jar is not None
        self._grounder = VisualGrounder()

        if self._available:
            logger.info("SikuliX encontrado", jar=self._jar)
        else:
            logger.warning("SikuliX não encontrado, usando template matching via OpenCV")

    def _find_sikulix(self) -> Optional[str]:
        """Localiza sikulix-ide.jar ou sikulixapi.jar."""
        candidates = [
            Path.home() / ".local/lib/sikulix/sikulixapi.jar",
            Path("/opt/sikulix/sikulixapi.jar"),
            Path("/usr/local/lib/sikulixapi.jar"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def find_on_screen(self, template_path: str, confidence: float = 0.85) -> Optional[tuple[int, int]]:
        """
        Localiza template na tela.
        Retorna (x, y) do centro ou None.
        """
        if self._available and self._jar:
            return self._find_via_sikulix(template_path, confidence)
        else:
            return self._find_via_opencv(template_path, confidence)

    def _find_via_sikulix(self, template_path: str, confidence: float) -> Optional[tuple[int, int]]:
        """Usa SikuliX via linha de comando."""
        try:
            script = (
                f"from sikuli import *\n"
                f"match = find(Pattern('{template_path}').similar({confidence}))\n"
                f"if match:\n"
                f"    print(match.x + match.w/2, match.y + match.h/2)\n"
            )
            with __import__("tempfile").NamedTemporaryFile(mode="w", suffix=".sikuli", delete=False) as f:
                f.write(script)
                script_path = f.name

            result = subprocess.run(
                ["java", "-jar", self._jar, "-r", script_path],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    return int(float(parts[0])), int(float(parts[1]))
        except Exception as e:
            logger.debug("SikuliX falhou", error=str(e))
        return None

    def _find_via_opencv(self, template_path: str, confidence: float) -> Optional[tuple[int, int]]:
        """Usa OpenCV template matching como fallback."""
        result = self._grounder.find_by_template(template_path, threshold=confidence)
        if result.found and result.bbox:
            x = result.bbox[0] + result.bbox[2] // 2
            y = result.bbox[1] + result.bbox[3] // 2
            return x, y
        return None


class CADAgent:
    """
    Agente especialista em CAD/aplicativos Windows via Wine.
    Combina PyAutoGUI (visual fallback) com SikuliX (template matching).
    """

    def __init__(self):
        self.input = InputController()
        self.sikulix = SikuliXBridge()
        self._detected_app: Optional[str] = None
        self._wine_prefix = Path.home() / ".wine"

    def detect_cad_app(self) -> Optional[str]:
        """Detecta qual CAD está aberto via nome da janela."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2,
            )
            win_name = result.stdout.strip().lower()
            for cad in ["fusion", "rhino", "coreldraw", "autocad", "solidworks", "blender"]:
                if cad in win_name:
                    self._detected_app = cad
                    return cad
        except Exception:
            pass
        return None

    def execute_action(self, action: CADAction) -> CADResult:
        """Executa ação CAD."""
        app = self._detected_app or self.detect_cad_app()

        if action.action_type == "hotkey":
            key = action.key or ""
            # Resolve atalho semântico para o CAD ativo
            if app and key in CAD_HOTKEYS.get(app.replace(" ", "").lower(), {}):
                key = CAD_HOTKEYS[app][key]
            self.input.press_key(key)
            return CADResult(success=True, method="pyautogui")

        elif action.action_type == "tool_select" and action.tool_name:
            return self._select_tool(action.tool_name, app)

        elif action.action_type == "template" and action.template_path:
            pos = self.sikulix.find_on_screen(action.template_path)
            if pos:
                self.input.click(*pos)
                return CADResult(success=True, method="sikulix", data=pos)
            return CADResult(success=False, method="sikulix", error="Template não encontrado")

        elif action.action_type == "click":
            if action.x is not None and action.y is not None:
                self.input.click(action.x, action.y)
                return CADResult(success=True, method="pyautogui")

            # Tenta localizar por nome via SikuliX/OCR
            if action.target:
                from neopilot.perception.visual_grounder import VisualGrounder
                grounder = VisualGrounder()
                result = grounder.find_by_text(action.target)
                if result.found and result.bbox:
                    x = result.bbox[0] + result.bbox[2] // 2
                    y = result.bbox[1] + result.bbox[3] // 2
                    self.input.click(x, y)
                    return CADResult(success=True, method="ocr_click")

        elif action.action_type == "type" and action.text:
            self.input.type_text(action.text)
            return CADResult(success=True, method="pyautogui")

        elif action.action_type == "macro":
            return self._run_cad_macro(action, app)

        return CADResult(success=False, method="none", error="Ação não suportada")

    def _select_tool(self, tool_name: str, app: Optional[str]) -> CADResult:
        """Seleciona ferramenta CAD por nome."""
        if not app:
            return CADResult(success=False, method="none", error="App CAD não detectado")

        hotkeys = CAD_HOTKEYS.get(app.replace(" ", "").lower(), {})
        if tool_name.lower() in hotkeys:
            key = hotkeys[tool_name.lower()]
            self.input.press_key(key)
            return CADResult(success=True, method="hotkey", data=key)

        # Tenta via Command Line no AutoCAD
        if "autocad" in app.lower():
            self.input.type_text(f"{tool_name}\n")
            return CADResult(success=True, method="autocad_cli")

        # Fallback: busca visual pelo nome da ferramenta
        from neopilot.perception.visual_grounder import VisualGrounder
        grounder = VisualGrounder()
        result = grounder.find_by_text(tool_name)
        if result.found and result.bbox:
            x = result.bbox[0] + result.bbox[2] // 2
            y = result.bbox[1] + result.bbox[3] // 2
            self.input.click(x, y)
            return CADResult(success=True, method="visual_search")

        return CADResult(success=False, method="none", error=f"Ferramenta '{tool_name}' não encontrada")

    def _run_cad_macro(self, action: CADAction, app: Optional[str]) -> CADResult:
        """Executa macro/script no CAD."""
        if action.text and "autocad" in (app or "").lower():
            # AutoCAD aceita scripts via command line
            for line in action.text.split("\n"):
                self.input.type_text(line + "\n")
                time.sleep(0.1)
            return CADResult(success=True, method="autocad_macro")

        return CADResult(success=False, method="none", error="Macro não suportado para este CAD")

    def open_wine_app(self, exe_path: str, wine_prefix: Optional[str] = None) -> CADResult:
        """Abre aplicativo Windows via Wine."""
        prefix = wine_prefix or str(self._wine_prefix)
        env = {**__import__("os").environ, "WINEPREFIX": prefix}
        try:
            subprocess.Popen(
                ["wine", exe_path],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)  # Aguarda inicialização
            logger.info("App Wine iniciado", exe=exe_path)
            return CADResult(success=True, method="wine_cli")
        except Exception as e:
            logger.error("Falha ao iniciar app Wine", error=str(e))
            return CADResult(success=False, method="wine_cli", error=str(e))

    def take_cad_screenshot(self, output_path: str) -> bool:
        """Captura screenshot da janela CAD ativa."""
        try:
            from neopilot.perception.screen_capture import ScreenCapture
            cap = ScreenCapture()
            screenshot = cap.capture()
            screenshot.to_pil().save(output_path)
            return True
        except Exception as e:
            logger.error("Screenshot CAD falhou", error=str(e))
            return False
