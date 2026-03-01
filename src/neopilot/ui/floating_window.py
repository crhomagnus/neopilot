"""
NeoPilot Mini-Janela Flutuante (300×400px)
GTK4 always-on-top com ícone na system tray.
Fallback para Qt6 (PyQt6) se GTK4 não disponível.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from neopilot.core.logger import get_logger

logger = get_logger("ui")


class AgentStatus(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"      # human-in-the-loop
    ERROR = "error"
    PROFESSOR = "professor"  # Modo Professor ativo


@dataclass
class ChatMessage:
    role: str  # "user" | "agent" | "system" | "error"
    content: str
    timestamp: float = 0.0
    action_type: Optional[str] = None

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ConfirmationRequest:
    action_type: str
    description: str
    callback_approve: Callable
    callback_deny: Callable


class FloatingWindowBase:
    """Interface base para janelas flutuantes."""

    WIDTH = 300
    HEIGHT = 400

    def __init__(self):
        self._status = AgentStatus.IDLE
        self._messages: list[ChatMessage] = []
        self._on_user_input: Optional[Callable[[str], None]] = None
        self._on_voice_toggle: Optional[Callable] = None
        self._on_approve: Optional[Callable] = None
        self._on_deny: Optional[Callable] = None
        self._pending_confirmation: Optional[ConfirmationRequest] = None
        self._professor_mode = False
        self._update_queue: queue.Queue = queue.Queue()

    def on_user_input(self, callback: Callable[[str], None]) -> None:
        self._on_user_input = callback

    def on_voice_toggle(self, callback: Callable) -> None:
        self._on_voice_toggle = callback

    def set_status(self, status: AgentStatus) -> None:
        self._status = status
        self._update_queue.put(("status", status))

    def add_message(self, message: ChatMessage) -> None:
        self._messages.append(message)
        self._update_queue.put(("message", message))

    def show_confirmation(self, request: ConfirmationRequest) -> None:
        self._pending_confirmation = request
        self._update_queue.put(("confirmation", request))

    def set_professor_mode(self, enabled: bool) -> None:
        self._professor_mode = enabled
        self._update_queue.put(("professor", enabled))

    def run(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class GTK4FloatingWindow(FloatingWindowBase):
    """
    Mini-janela flutuante usando GTK4.
    300×400px, always-on-top, bordas arredondadas, transparência.
    """

    def __init__(self):
        super().__init__()
        self._app = None
        self._window = None
        self._chat_list = None
        self._input_entry = None
        self._status_label = None
        self._voice_btn = None
        self._confirm_box = None
        self._available = False
        self._check_gtk4()

    def _check_gtk4(self) -> None:
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            gi.require_version("Adw", "1")
            self._available = True
        except (ImportError, ValueError):
            try:
                import gi
                gi.require_version("Gtk", "4.0")
                self._available = True
            except Exception:
                logger.warning("GTK4 não disponível")

    def run(self) -> None:
        if not self._available:
            logger.warning("GTK4 não disponível, usando fallback de console")
            self._run_console_fallback()
            return

        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk, GLib

            self._app = Gtk.Application(application_id="com.neopilot.overlay")
            self._app.connect("activate", self._on_activate)

            # Thread para processar updates da queue
            GLib.timeout_add(100, self._process_queue)

            self._app.run([])
        except Exception as e:
            logger.error("GTK4 falhou", error=str(e))
            self._run_console_fallback()

    def _on_activate(self, app: Any) -> None:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk, Gdk

        # Janela principal
        self._window = Gtk.ApplicationWindow(application=app)
        self._window.set_title("NeoPilot")
        self._window.set_default_size(self.WIDTH, self.HEIGHT)
        self._window.set_resizable(False)

        # Always on top via display hints
        self._window.set_decorated(True)

        # CSS customizado
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(self._get_css().encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Layout principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)

        # Header: status + botão voz
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self._status_label = Gtk.Label(label="● Idle")
        self._status_label.add_css_class("status-idle")
        header.append(self._status_label)

        # Separador elástico
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        self._voice_btn = Gtk.Button(label="🎤")
        self._voice_btn.connect("clicked", self._on_voice_click)
        self._voice_btn.add_css_class("voice-btn")
        header.append(self._voice_btn)

        # Botão professor mode
        prof_btn = Gtk.ToggleButton(label="🎓")
        prof_btn.connect("toggled", self._on_professor_toggle)
        prof_btn.set_tooltip_text("Ativar Modo Professor")
        header.append(prof_btn)

        vbox.append(header)

        # Separador
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.append(sep)

        # Área de chat (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._chat_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.set_child(self._chat_list)
        vbox.append(scroll)

        # Caixa de confirmação (inicialmente oculta)
        self._confirm_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._confirm_box.set_visible(False)

        approve_btn = Gtk.Button(label="✓ Aprovar")
        approve_btn.add_css_class("approve-btn")
        approve_btn.connect("clicked", self._on_approve_click)
        self._confirm_box.append(approve_btn)

        deny_btn = Gtk.Button(label="✗ Negar")
        deny_btn.add_css_class("deny-btn")
        deny_btn.connect("clicked", self._on_deny_click)
        self._confirm_box.append(deny_btn)

        vbox.append(self._confirm_box)

        # Input de texto
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self._input_entry = Gtk.Entry()
        self._input_entry.set_placeholder_text("Digite ou fale um comando...")
        self._input_entry.set_hexpand(True)
        self._input_entry.connect("activate", self._on_send_click)
        input_box.append(self._input_entry)

        send_btn = Gtk.Button(label="➤")
        send_btn.connect("clicked", self._on_send_click)
        send_btn.add_css_class("send-btn")
        input_box.append(send_btn)

        vbox.append(input_box)
        self._window.set_child(vbox)
        self._window.present()

    def _get_css(self) -> str:
        return """
        window {
            background-color: rgba(28, 28, 35, 0.95);
            border-radius: 12px;
        }
        label { color: #e0e0e0; font-size: 12px; }
        .status-idle { color: #888888; font-weight: bold; }
        .status-listening { color: #4fc3f7; font-weight: bold; }
        .status-thinking { color: #ffb74d; font-weight: bold; }
        .status-acting { color: #81c784; font-weight: bold; }
        .status-waiting { color: #f06292; font-weight: bold; }
        .status-error { color: #e57373; font-weight: bold; }
        .status-professor { color: #ce93d8; font-weight: bold; }
        .msg-user {
            background-color: rgba(33, 150, 243, 0.3);
            border-radius: 8px;
            padding: 6px 10px;
            margin: 2px 20px 2px 4px;
            color: #bbdefb;
        }
        .msg-agent {
            background-color: rgba(76, 175, 80, 0.2);
            border-radius: 8px;
            padding: 6px 10px;
            margin: 2px 4px 2px 20px;
            color: #c8e6c9;
        }
        .msg-system {
            color: #9e9e9e;
            font-style: italic;
            padding: 2px 8px;
        }
        .msg-error {
            background-color: rgba(244, 67, 54, 0.2);
            border-radius: 8px;
            padding: 4px 8px;
            color: #ef9a9a;
        }
        entry {
            background-color: rgba(255, 255, 255, 0.08);
            color: #e0e0e0;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 6px;
            font-size: 12px;
        }
        button {
            background-color: rgba(255,255,255,0.08);
            color: #e0e0e0;
            border: none;
            border-radius: 8px;
            padding: 4px 10px;
        }
        button:hover { background-color: rgba(255,255,255,0.15); }
        .voice-btn { color: #4fc3f7; }
        .send-btn { color: #81c784; }
        .approve-btn { color: #81c784; background-color: rgba(76,175,80,0.2); }
        .deny-btn { color: #e57373; background-color: rgba(244,67,54,0.2); }
        """

    def _process_queue(self) -> bool:
        """Processa updates da queue (chamado no main loop GTK)."""
        try:
            while True:
                update_type, data = self._update_queue.get_nowait()
                if update_type == "status":
                    self._update_status_label(data)
                elif update_type == "message":
                    self._add_message_widget(data)
                elif update_type == "confirmation":
                    self._show_confirmation_ui(data)
                elif update_type == "professor":
                    self._toggle_professor_ui(data)
        except queue.Empty:
            pass
        return True  # Continua o timeout

    def _update_status_label(self, status: AgentStatus) -> None:
        if not self._status_label:
            return
        icons = {
            AgentStatus.IDLE: "● Idle",
            AgentStatus.LISTENING: "🎤 Ouvindo...",
            AgentStatus.THINKING: "💭 Pensando...",
            AgentStatus.ACTING: "⚡ Executando...",
            AgentStatus.WAITING: "⏳ Aguardando...",
            AgentStatus.ERROR: "✗ Erro",
            AgentStatus.PROFESSOR: "🎓 Modo Professor",
        }
        css_class = f"status-{status.value}"
        self._status_label.set_text(icons.get(status, "●"))
        for cls in ["status-idle", "status-listening", "status-thinking",
                    "status-acting", "status-waiting", "status-error", "status-professor"]:
            self._status_label.remove_css_class(cls)
        self._status_label.add_css_class(css_class)

    def _add_message_widget(self, msg: ChatMessage) -> None:
        if not self._chat_list:
            return

        from gi.repository import Gtk

        label = Gtk.Label(label=msg.content)
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_max_width_chars(32)
        label.add_css_class(f"msg-{msg.role}")

        self._chat_list.append(label)

        # Auto-scroll para o final
        adj = self._chat_list.get_parent().get_vadjustment() if self._chat_list.get_parent() else None
        if adj:
            adj.set_value(adj.get_upper())

    def _show_confirmation_ui(self, request: ConfirmationRequest) -> None:
        if self._confirm_box:
            self._confirm_box.set_visible(True)
        self.add_message(ChatMessage(
            role="system",
            content=f"⚠ Confirmar: {request.description}"
        ))

    def _toggle_professor_ui(self, enabled: bool) -> None:
        if enabled:
            self.add_message(ChatMessage(role="system", content="🎓 Modo Professor ativado"))

    def _on_voice_click(self, _btn: Any) -> None:
        if self._on_voice_toggle:
            self._on_voice_toggle()

    def _on_professor_toggle(self, btn: Any) -> None:
        enabled = btn.get_active()
        self.set_professor_mode(enabled)

    def _on_send_click(self, _widget: Any) -> None:
        if not self._input_entry:
            return
        text = self._input_entry.get_text().strip()
        if not text:
            return
        # Sempre mostra a mensagem do usuário no chat
        self.add_message(ChatMessage(role="user", content=text))
        self._input_entry.set_text("")
        if self._on_user_input:
            self._on_user_input(text)
        else:
            self.add_message(ChatMessage(
                role="system",
                content="Inicie com 'neopilot chat' para conectar o agente.",
            ))

    def _on_approve_click(self, _btn: Any) -> None:
        if self._pending_confirmation:
            self._pending_confirmation.callback_approve()
            self._pending_confirmation = None
        if self._confirm_box:
            self._confirm_box.set_visible(False)

    def _on_deny_click(self, _btn: Any) -> None:
        if self._pending_confirmation:
            self._pending_confirmation.callback_deny()
            self._pending_confirmation = None
        if self._confirm_box:
            self._confirm_box.set_visible(False)

    def _run_console_fallback(self) -> None:
        """Fallback simples de console quando GTK4 não está disponível."""
        logger.info("Rodando em modo console (sem GUI)")
        print("\n" + "="*40)
        print("  NeoPilot — Modo Console")
        print("="*40)
        print("Digite comandos ou 'sair' para encerrar\n")

        while True:
            try:
                text = input("Você: ").strip()
                if text.lower() in ("sair", "exit", "quit"):
                    break
                if text and self._on_user_input:
                    self._on_user_input(text)
            except (KeyboardInterrupt, EOFError):
                break

    def stop(self) -> None:
        if self._app:
            self._app.quit()


class Qt6FloatingWindow(FloatingWindowBase):
    """Fallback usando PyQt6 se GTK4 não disponível."""

    def __init__(self):
        super().__init__()
        self._available = False
        try:
            from PyQt6.QtWidgets import QApplication
            self._available = True
        except ImportError:
            pass

    def run(self) -> None:
        if not self._available:
            GTK4FloatingWindow._run_console_fallback(self)
            return

        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout,
            QHBoxLayout, QLabel, QPushButton, QLineEdit,
            QScrollArea, QFrame,
        )
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QColor
        import sys

        app = QApplication(sys.argv)
        app.setStyleSheet(self._get_qt_style())

        win = QMainWindow()
        win.setWindowTitle("NeoPilot")
        win.setFixedSize(self.WIDTH, self.HEIGHT)
        win.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)

        central = QWidget()
        win.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Status bar
        self._qt_status = QLabel("● Idle")
        layout.addWidget(self._qt_status)

        # Chat area
        scroll = QScrollArea()
        self._qt_chat = QWidget()
        self._qt_chat_layout = QVBoxLayout(self._qt_chat)
        scroll.setWidget(self._qt_chat)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)

        # Input
        input_row = QHBoxLayout()
        self._qt_input = QLineEdit()
        self._qt_input.setPlaceholderText("Digite um comando...")
        self._qt_input.returnPressed.connect(self._qt_send)
        input_row.addWidget(self._qt_input)

        send_btn = QPushButton("➤")
        send_btn.clicked.connect(self._qt_send)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        # Timer para processar queue
        timer = QTimer()
        timer.timeout.connect(self._qt_process_queue)
        timer.start(100)

        win.show()
        app.exec()

    def _qt_send(self) -> None:
        text = self._qt_input.text().strip()
        if not text:
            return
        self.add_message(ChatMessage(role="user", content=text))
        self._qt_input.clear()
        if self._on_user_input:
            self._on_user_input(text)
        else:
            self.add_message(ChatMessage(
                role="system",
                content="Inicie com 'neopilot chat' para conectar o agente.",
            ))

    def _qt_process_queue(self) -> None:
        try:
            while True:
                update_type, data = self._update_queue.get_nowait()
                if update_type == "message":
                    self._qt_add_message(data)
        except queue.Empty:
            pass

    def _qt_add_message(self, msg: ChatMessage) -> None:
        from PyQt6.QtWidgets import QLabel
        label = QLabel(msg.content)
        label.setWordWrap(True)
        self._qt_chat_layout.addWidget(label)

    def _get_qt_style(self) -> str:
        return """
        QMainWindow { background-color: #1c1c23; }
        QWidget { background-color: #1c1c23; color: #e0e0e0; font-size: 12px; }
        QLineEdit {
            background-color: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px;
            padding: 4px;
            color: #e0e0e0;
        }
        QPushButton {
            background-color: rgba(255,255,255,0.08);
            border: none;
            border-radius: 6px;
            padding: 4px 10px;
            color: #e0e0e0;
        }
        QPushButton:hover { background-color: rgba(255,255,255,0.15); }
        QScrollArea { border: none; }
        """

    def stop(self) -> None:
        pass


def create_floating_window() -> FloatingWindowBase:
    """Factory: cria janela GTK4 ou Qt6 dependendo da disponibilidade."""
    gtk_win = GTK4FloatingWindow()
    if gtk_win._available:
        return gtk_win

    qt_win = Qt6FloatingWindow()
    if qt_win._available:
        return qt_win

    logger.warning("Nenhum toolkit GUI disponível, usando modo console")
    return gtk_win  # usará o fallback console interno
