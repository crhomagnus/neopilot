"""
NeoPilot Mini-Janela Flutuante (300×420px)
GTK4 always-on-top com conexão automática ao agente.
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
    DISCONNECTED = "disconnected"   # Agente não iniciado
    CONNECTING = "connecting"       # Inicializando
    IDLE = "idle"                   # Pronto
    LISTENING = "listening"         # Ouvindo microfone
    THINKING = "thinking"           # Processando
    ACTING = "acting"               # Executando ação
    WAITING = "waiting"             # Aguardando confirmação
    ERROR = "error"                 # Erro
    PROFESSOR = "professor"         # Modo Professor


@dataclass
class ChatMessage:
    role: str   # "user" | "agent" | "system" | "error"
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
    HEIGHT = 420

    def __init__(self):
        self._status = AgentStatus.DISCONNECTED
        self._messages: list[ChatMessage] = []
        self._on_user_input: Optional[Callable[[str], None]] = None
        self._on_voice_toggle: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._pending_confirmation: Optional[ConfirmationRequest] = None
        self._professor_mode = False
        self._update_queue: queue.Queue = queue.Queue()

    def on_user_input(self, callback: Callable[[str], None]) -> None:
        self._on_user_input = callback

    def on_voice_toggle(self, callback: Callable) -> None:
        self._on_voice_toggle = callback

    def on_connect(self, callback: Callable) -> None:
        """Callback chamado quando usuário clica em 'Iniciar Agente'."""
        self._on_connect = callback

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
    Mini-janela flutuante GTK4.
    Autocontida: inicia o agente internamente ao clicar em 'Iniciar'.
    """

    # Mapa status → (ícone, texto, css-class)
    STATUS_MAP = {
        AgentStatus.DISCONNECTED: ("⬤", "Desconectado",  "s-off"),
        AgentStatus.CONNECTING:   ("⬤", "Conectando…",   "s-wait"),
        AgentStatus.IDLE:         ("⬤", "Pronto",        "s-on"),
        AgentStatus.LISTENING:    ("⬤", "Ouvindo…",      "s-listen"),
        AgentStatus.THINKING:     ("⬤", "Pensando…",     "s-think"),
        AgentStatus.ACTING:       ("⬤", "Executando…",   "s-act"),
        AgentStatus.WAITING:      ("⬤", "Aguardando…",   "s-wait"),
        AgentStatus.ERROR:        ("⬤", "Erro",          "s-err"),
        AgentStatus.PROFESSOR:    ("⬤", "Prof. Ativo",   "s-prof"),
    }

    def __init__(self):
        super().__init__()
        self._app = None
        self._window = None
        self._chat_list = None
        self._scroll = None
        self._input_entry = None
        self._send_btn = None
        self._status_dot = None
        self._status_label = None
        self._connect_banner = None   # banner "Iniciar Agente"
        self._confirm_box = None
        self._available = False
        self._glib = None
        self._check_gtk4()

    def _check_gtk4(self) -> None:
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk  # noqa: F401
            self._available = True
        except Exception:
            logger.warning("GTK4 não disponível")

    # ── run ────────────────────────────────────────────────────────────────

    def run(self) -> None:
        if not self._available:
            self._run_console_fallback()
            return
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk, GLib
            self._glib = GLib

            self._app = Gtk.Application(application_id="com.neopilot.overlay")
            self._app.connect("activate", self._on_activate)
            GLib.timeout_add(80, self._process_queue)
            self._app.run([])
        except Exception as e:
            logger.error("GTK4 falhou", error=str(e))
            self._run_console_fallback()

    def stop(self) -> None:
        if self._app:
            self._app.quit()

    # ── build UI ───────────────────────────────────────────────────────────

    def _on_activate(self, app: Any) -> None:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk, Gdk

        win = Gtk.ApplicationWindow(application=app)
        win.set_title("NeoPilot")
        win.set_default_size(self.WIDTH, self.HEIGHT)
        win.set_resizable(True)
        self._window = win

        # CSS
        css = Gtk.CssProvider()
        css.load_from_data(self._css().encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_margin_top(0)
        root.set_margin_bottom(8)
        root.set_margin_start(8)
        root.set_margin_end(8)

        # ── Header ──
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_top(8)
        header.set_margin_bottom(6)

        title = Gtk.Label(label="NeoPilot")
        title.add_css_class("title")
        header.append(title)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        # Indicador de status (ponto + texto)
        self._status_dot = Gtk.Label(label="⬤")
        self._status_dot.add_css_class("s-off")
        header.append(self._status_dot)

        self._status_label = Gtk.Label(label="Desconectado")
        self._status_label.add_css_class("status-text")
        header.append(self._status_label)

        # Botão voz
        self._voice_btn = Gtk.Button(label="🎤")
        self._voice_btn.add_css_class("icon-btn")
        self._voice_btn.connect("clicked", self._on_voice_click)
        self._voice_btn.set_tooltip_text("Ativar/desativar microfone")
        header.append(self._voice_btn)

        # Botão professor
        prof_btn = Gtk.ToggleButton(label="🎓")
        prof_btn.add_css_class("icon-btn")
        prof_btn.set_tooltip_text("Modo Professor")
        prof_btn.connect("toggled", self._on_professor_toggle)
        header.append(prof_btn)

        root.append(header)

        # Separador
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        root.append(sep)

        # ── Banner "Iniciar Agente" (visível enquanto desconectado) ──
        self._connect_banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._connect_banner.set_margin_top(24)
        self._connect_banner.set_margin_bottom(12)
        self._connect_banner.set_margin_start(16)
        self._connect_banner.set_margin_end(16)
        self._connect_banner.set_valign(Gtk.Align.CENTER)
        self._connect_banner.set_vexpand(True)

        robot_lbl = Gtk.Label(label="🤖")
        robot_lbl.add_css_class("robot-icon")
        self._connect_banner.append(robot_lbl)

        hello_lbl = Gtk.Label(label="Olá! Sou o NeoPilot.")
        hello_lbl.add_css_class("hello-text")
        hello_lbl.set_wrap(True)
        hello_lbl.set_justify(Gtk.Justification.CENTER)
        self._connect_banner.append(hello_lbl)

        sub_lbl = Gtk.Label(
            label="Posso abrir apps, navegar na web,\n"
                  "escrever documentos e muito mais.\n"
                  "Clique para começar."
        )
        sub_lbl.add_css_class("sub-text")
        sub_lbl.set_wrap(True)
        sub_lbl.set_justify(Gtk.Justification.CENTER)
        self._connect_banner.append(sub_lbl)

        connect_btn = Gtk.Button(label="  Iniciar Agente  ")
        connect_btn.add_css_class("connect-btn")
        connect_btn.connect("clicked", self._on_connect_click)
        connect_btn.set_halign(Gtk.Align.CENTER)
        self._connect_banner.append(connect_btn)

        root.append(self._connect_banner)

        # ── Área de chat (oculta até conectar) ──
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_visible(False)

        self._chat_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._chat_list.set_margin_top(6)
        self._chat_list.set_margin_bottom(4)
        self._scroll.set_child(self._chat_list)
        root.append(self._scroll)

        # ── Caixa de confirmação ──
        self._confirm_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._confirm_box.set_visible(False)
        self._confirm_box.set_margin_top(4)

        approve_btn = Gtk.Button(label="✓ Aprovar")
        approve_btn.add_css_class("approve-btn")
        approve_btn.connect("clicked", self._on_approve_click)
        approve_btn.set_hexpand(True)
        self._confirm_box.append(approve_btn)

        deny_btn = Gtk.Button(label="✗ Cancelar")
        deny_btn.add_css_class("deny-btn")
        deny_btn.connect("clicked", self._on_deny_click)
        deny_btn.set_hexpand(True)
        self._confirm_box.append(deny_btn)

        root.append(self._confirm_box)

        # ── Input ──
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        input_box.set_margin_top(6)

        self._input_entry = Gtk.Entry()
        self._input_entry.set_placeholder_text("Digite um comando…")
        self._input_entry.set_hexpand(True)
        self._input_entry.connect("activate", self._on_send_click)
        self._input_entry.set_sensitive(False)   # Desabilitado até conectar
        input_box.append(self._input_entry)

        self._send_btn = Gtk.Button(label="➤")
        self._send_btn.add_css_class("send-btn")
        self._send_btn.connect("clicked", self._on_send_click)
        self._send_btn.set_sensitive(False)      # Desabilitado até conectar
        input_box.append(self._send_btn)

        root.append(input_box)
        win.set_child(root)
        win.present()

    # ── CSS ───────────────────────────────────────────────────────────────

    def _css(self) -> str:
        return """
        window {
            background-color: #1a1a24;
        }
        /* Título */
        .title {
            color: #a78bfa;
            font-weight: bold;
            font-size: 13px;
        }
        /* Status dot */
        .s-off    { color: #555566; font-size: 10px; }
        .s-on     { color: #4ade80; font-size: 10px; }
        .s-wait   { color: #fbbf24; font-size: 10px; }
        .s-listen { color: #38bdf8; font-size: 10px; }
        .s-think  { color: #fb923c; font-size: 10px; }
        .s-act    { color: #4ade80; font-size: 10px; }
        .s-err    { color: #f87171; font-size: 10px; }
        .s-prof   { color: #c084fc; font-size: 10px; }
        .status-text {
            color: #888899;
            font-size: 10px;
            margin-right: 4px;
        }
        /* Banner de boas-vindas */
        .robot-icon { font-size: 36px; margin-bottom: 4px; }
        .hello-text { color: #e2e8f0; font-size: 13px; font-weight: bold; }
        .sub-text   { color: #94a3b8; font-size: 11px; margin-top: 4px; }
        /* Botão conectar */
        .connect-btn {
            background-color: #7c3aed;
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 8px 20px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 12px;
        }
        .connect-btn:hover { background-color: #6d28d9; }
        /* Mensagens */
        .msg-user {
            background-color: rgba(124, 58, 237, 0.35);
            border-radius: 10px 10px 2px 10px;
            padding: 6px 10px;
            margin: 2px 4px 2px 30px;
            color: #ddd6fe;
            font-size: 12px;
        }
        .msg-agent {
            background-color: rgba(30, 41, 59, 0.9);
            border-radius: 10px 10px 10px 2px;
            padding: 6px 10px;
            margin: 2px 30px 2px 4px;
            color: #e2e8f0;
            font-size: 12px;
        }
        .msg-system {
            color: #64748b;
            font-style: italic;
            font-size: 11px;
            padding: 2px 8px;
        }
        .msg-error {
            background-color: rgba(239, 68, 68, 0.2);
            border-radius: 8px;
            padding: 4px 8px;
            color: #fca5a5;
            font-size: 12px;
        }
        /* Separador */
        separator { background-color: #2d2d3d; min-height: 1px; }
        /* Input */
        entry {
            background-color: #252535;
            color: #e2e8f0;
            border: 1px solid #3d3d50;
            border-radius: 10px;
            padding: 7px 10px;
            font-size: 12px;
        }
        entry:focus { border-color: #7c3aed; }
        /* Botões gerais */
        .icon-btn {
            background-color: transparent;
            border: none;
            border-radius: 6px;
            padding: 3px 6px;
            color: #94a3b8;
            font-size: 13px;
        }
        .icon-btn:hover { background-color: rgba(255,255,255,0.08); }
        .send-btn {
            background-color: #7c3aed;
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 6px 12px;
            font-size: 13px;
        }
        .send-btn:hover { background-color: #6d28d9; }
        .send-btn:disabled { background-color: #3d3d50; color: #666; }
        .approve-btn {
            background-color: rgba(74,222,128,0.2);
            color: #4ade80;
            border: 1px solid rgba(74,222,128,0.4);
            border-radius: 8px;
            padding: 5px;
        }
        .deny-btn {
            background-color: rgba(248,113,113,0.2);
            color: #f87171;
            border: 1px solid rgba(248,113,113,0.4);
            border-radius: 8px;
            padding: 5px;
        }
        label { color: #e2e8f0; }
        """

    # ── Queue processing ──────────────────────────────────────────────────

    def _process_queue(self) -> bool:
        try:
            while True:
                update_type, data = self._update_queue.get_nowait()
                if update_type == "status":
                    self._apply_status(data)
                elif update_type == "message":
                    self._append_message(data)
                elif update_type == "confirmation":
                    self._show_confirm_ui(data)
                elif update_type == "professor":
                    if data:
                        self._append_message(ChatMessage(role="system", content="🎓 Modo Professor ativado"))
        except queue.Empty:
            pass
        return True

    def _apply_status(self, status: AgentStatus) -> None:
        dot_txt, label_txt, css = self.STATUS_MAP.get(status, ("⬤", str(status), "s-off"))
        if self._status_dot:
            for c in [v[2] for v in self.STATUS_MAP.values()]:
                self._status_dot.remove_css_class(c)
            self._status_dot.add_css_class(css)
        if self._status_label:
            self._status_label.set_text(label_txt)

        # Ao conectar: oculta banner, mostra chat, habilita input
        if status not in (AgentStatus.DISCONNECTED, AgentStatus.CONNECTING):
            if self._connect_banner and self._connect_banner.get_visible():
                self._connect_banner.set_visible(False)
                if self._scroll:
                    self._scroll.set_visible(True)
                if self._input_entry:
                    self._input_entry.set_sensitive(True)
                    self._input_entry.grab_focus()
                if self._send_btn:
                    self._send_btn.set_sensitive(True)
        elif status == AgentStatus.CONNECTING:
            # Troca banner por spinner de texto
            if self._connect_banner:
                pass  # o label de status já indica "Conectando…"

    def _append_message(self, msg: ChatMessage) -> None:
        if not self._chat_list:
            return
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        label = Gtk.Label(label=msg.content)
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_max_width_chars(30)
        label.add_css_class(f"msg-{msg.role}")
        self._chat_list.append(label)

        # Scroll para o final
        if self._scroll:
            adj = self._scroll.get_vadjustment()
            if adj:
                self._glib.idle_add(lambda: adj.set_value(adj.get_upper()))

    def _show_confirm_ui(self, request: ConfirmationRequest) -> None:
        if self._confirm_box:
            self._confirm_box.set_visible(True)
        self._append_message(ChatMessage(role="system", content=f"⚠ Confirmar: {request.description}"))

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_connect_click(self, _btn: Any) -> None:
        """Usuário clicou em 'Iniciar Agente'."""
        self.set_status(AgentStatus.CONNECTING)
        self._append_message(ChatMessage(role="system", content="Iniciando agente, aguarde…"))
        if self._on_connect:
            self._on_connect()
        else:
            # Auto-conecta sem precisar do CLI
            self._auto_connect()

    def _auto_connect(self) -> None:
        """Inicializa o orquestrador internamente em background."""
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        self._loop = loop

        async def _init():
            from neopilot.core.agent_graph import NeoPilotOrchestrator
            from neopilot.voice.tts import TTSEngine

            orch = NeoPilotOrchestrator()
            await orch.initialize()
            self._orchestrator = orch
            self._tts = TTSEngine()

            def _run_task(task: str) -> None:
                self.set_status(AgentStatus.THINKING)

                async def _exec():
                    return await orch.run_task(task)

                def _done(fut):
                    try:
                        result = fut.result()
                        success = result.get("success", False)
                        msg = result.get("result", "Concluído")
                        self.add_message(ChatMessage(
                            role="agent" if success else "error",
                            content=msg,
                        ))
                    except Exception as e:
                        self.add_message(ChatMessage(role="error", content=f"Erro: {e}"))
                    finally:
                        self.set_status(AgentStatus.IDLE)

                fut = _asyncio.run_coroutine_threadsafe(_exec(), loop)
                fut.add_done_callback(_done)

            self._on_user_input = _run_task
            self.set_status(AgentStatus.IDLE)
            self.add_message(ChatMessage(
                role="agent",
                content="Pronto! Como posso ajudar?\n\nExemplos:\n• Abre o LibreOffice Writer\n• Pesquisa sobre Python 3.13\n• Cria um doc sobre IA",
            ))

        def _run_loop():
            loop.run_until_complete(_init())
            loop.run_forever()

        t = threading.Thread(target=_run_loop, daemon=True, name="neopilot-agent")
        t.start()

    def _on_send_click(self, _widget: Any) -> None:
        if not self._input_entry:
            return
        text = self._input_entry.get_text().strip()
        if not text:
            return
        self._append_message(ChatMessage(role="user", content=text))
        self._input_entry.set_text("")
        if self._on_user_input:
            self._on_user_input(text)

    def _on_voice_click(self, _btn: Any) -> None:
        if self._on_voice_toggle:
            self._on_voice_toggle()

    def _on_professor_toggle(self, btn: Any) -> None:
        self.set_professor_mode(btn.get_active())

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

    # ── Fallback console ──────────────────────────────────────────────────

    def _run_console_fallback(self) -> None:
        logger.info("Rodando em modo console (sem GUI)")
        print("\n" + "="*40)
        print("  NeoPilot — Modo Console")
        print("="*40)
        self._auto_connect()
        time.sleep(3)  # Aguarda init
        print("Pronto! Digite comandos ('sair' para encerrar)\n")
        while True:
            try:
                text = input("Você: ").strip()
                if text.lower() in ("sair", "exit", "quit"):
                    break
                if text and self._on_user_input:
                    self._on_user_input(text)
                    time.sleep(0.5)
            except (KeyboardInterrupt, EOFError):
                break


class Qt6FloatingWindow(FloatingWindowBase):
    """Fallback usando PyQt6 se GTK4 não disponível."""

    def __init__(self):
        super().__init__()
        self._available = False
        try:
            from PyQt6.QtWidgets import QApplication  # noqa: F401
            self._available = True
        except ImportError:
            pass

    def run(self) -> None:
        if not self._available:
            GTK4FloatingWindow()._run_console_fallback()
            return

        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout,
            QHBoxLayout, QLabel, QPushButton, QLineEdit,
            QScrollArea, QFrame,
        )
        from PyQt6.QtCore import Qt, QTimer
        import sys

        app = QApplication(sys.argv)
        app.setStyleSheet(self._qt_css())

        win = QMainWindow()
        win.setWindowTitle("NeoPilot")
        win.setFixedSize(self.WIDTH, self.HEIGHT)
        win.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)

        central = QWidget()
        win.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("NeoPilot")
        title.setStyleSheet("color:#a78bfa; font-weight:bold; font-size:13px;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._qt_status = QLabel("⬤ Desconectado")
        self._qt_status.setStyleSheet("color:#555566; font-size:10px;")
        hdr.addWidget(self._qt_status)
        layout.addLayout(hdr)

        # Banner conectar
        self._qt_banner = QWidget()
        bl = QVBoxLayout(self._qt_banner)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl = QLabel("🤖"); rl.setStyleSheet("font-size:36px;"); rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(rl)
        hl = QLabel("Olá! Sou o NeoPilot."); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(hl)
        sl = QLabel("Clique para começar."); sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.setStyleSheet("color:#94a3b8; font-size:11px;")
        bl.addWidget(sl)
        self._qt_connect_btn = QPushButton("Iniciar Agente")
        self._qt_connect_btn.setStyleSheet(
            "background:#7c3aed; color:#fff; border-radius:8px; padding:8px 20px; font-weight:bold;"
        )
        self._qt_connect_btn.clicked.connect(self._qt_on_connect)
        bl.addWidget(self._qt_connect_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._qt_banner, stretch=1)

        # Chat
        self._qt_scroll = QScrollArea()
        self._qt_chat = QWidget()
        self._qt_chat_layout = QVBoxLayout(self._qt_chat)
        self._qt_chat_layout.addStretch()
        self._qt_scroll.setWidget(self._qt_chat)
        self._qt_scroll.setWidgetResizable(True)
        self._qt_scroll.setVisible(False)
        layout.addWidget(self._qt_scroll, stretch=1)

        # Input
        input_row = QHBoxLayout()
        self._qt_input = QLineEdit()
        self._qt_input.setPlaceholderText("Digite um comando…")
        self._qt_input.returnPressed.connect(self._qt_send)
        self._qt_input.setEnabled(False)
        input_row.addWidget(self._qt_input)
        self._qt_send_btn = QPushButton("➤")
        self._qt_send_btn.clicked.connect(self._qt_send)
        self._qt_send_btn.setEnabled(False)
        self._qt_send_btn.setStyleSheet(
            "background:#7c3aed; color:#fff; border-radius:8px; padding:6px 12px;"
        )
        input_row.addWidget(self._qt_send_btn)
        layout.addLayout(input_row)

        timer = QTimer()
        timer.timeout.connect(self._qt_process_queue)
        timer.start(80)

        win.show()
        app.exec()

    def _qt_on_connect(self) -> None:
        self.set_status(AgentStatus.CONNECTING)
        gtk_like = GTK4FloatingWindow.__new__(GTK4FloatingWindow)
        FloatingWindowBase.__init__(gtk_like)
        gtk_like._on_user_input = self._on_user_input
        gtk_like._update_queue = self._update_queue

        def forward_input(text):
            if self._on_user_input:
                self._on_user_input(text)

        self._on_user_input_forward = forward_input
        gtk_like._auto_connect_for(self)

    def _qt_send(self) -> None:
        text = self._qt_input.text().strip()
        if not text:
            return
        self.add_message(ChatMessage(role="user", content=text))
        self._qt_input.clear()
        if self._on_user_input:
            self._on_user_input(text)

    def _qt_process_queue(self) -> None:
        try:
            while True:
                update_type, data = self._update_queue.get_nowait()
                if update_type == "message":
                    self._qt_add_message(data)
                elif update_type == "status":
                    self._qt_apply_status(data)
        except queue.Empty:
            pass

    def _qt_apply_status(self, status: AgentStatus) -> None:
        _, label_txt, _ = GTK4FloatingWindow.STATUS_MAP.get(status, ("⬤", str(status), ""))
        if self._qt_status:
            self._qt_status.setText(f"⬤ {label_txt}")
        if status not in (AgentStatus.DISCONNECTED, AgentStatus.CONNECTING):
            if self._qt_banner and self._qt_banner.isVisible():
                self._qt_banner.setVisible(False)
                self._qt_scroll.setVisible(True)
                self._qt_input.setEnabled(True)
                self._qt_send_btn.setEnabled(True)

    def _qt_add_message(self, msg: ChatMessage) -> None:
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt
        label = QLabel(msg.content)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._qt_chat_layout.insertWidget(self._qt_chat_layout.count() - 1, label)

    def _qt_css(self) -> str:
        return """
        QMainWindow, QWidget { background-color: #1a1a24; color: #e2e8f0; font-size: 12px; }
        QLineEdit {
            background-color: #252535; border: 1px solid #3d3d50;
            border-radius: 8px; padding: 6px; color: #e2e8f0;
        }
        QPushButton { border-radius: 6px; padding: 4px 10px; color: #e2e8f0; }
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
    return gtk_win
