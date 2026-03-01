"""
NeoPilot Professor Dashboard
Dashboard em tempo real para professores monitorarem sessões de alunos.
FastAPI + WebSockets + Jinja2 templates.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

from neopilot.core.logger import get_logger

logger = get_logger("professor_dashboard")


@dataclass
class StudentSession:
    student_id: str
    student_name: str
    task: str
    started_at: float
    steps_total: int = 0
    steps_done: int = 0
    errors: list[dict] = None
    last_screenshot_b64: str = ""
    active: bool = True
    completion_pct: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ProfessorDashboard:
    """
    Servidor FastAPI com WebSockets para dashboard do professor.
    Fornece visão em tempo real de todas as sessões de alunos.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self._sessions: dict[str, StudentSession] = {}
        self._websockets: list[Any] = []
        self._app = None
        self._available = False
        self._check()

    def _check(self) -> None:
        try:
            import fastapi, websockets
            self._available = True
        except ImportError:
            logger.warning("FastAPI/websockets não disponível, dashboard desabilitado")

    def create_app(self) -> Any:
        """Cria e retorna aplicação FastAPI."""
        if not self._available:
            return None

        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse

        app = FastAPI(title="NeoPilot Professor Dashboard")
        self._app = app

        @app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return self._get_dashboard_html()

        @app.get("/api/sessions")
        async def list_sessions():
            return {
                "sessions": [asdict(s) for s in self._sessions.values()],
                "total": len(self._sessions),
                "active": sum(1 for s in self._sessions.values() if s.active),
            }

        @app.get("/api/sessions/{student_id}")
        async def get_session(student_id: str):
            session = self._sessions.get(student_id)
            if not session:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Sessão não encontrada")
            return asdict(session)

        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            self._websockets.append(ws)
            logger.info("Professor conectado via WebSocket")
            try:
                # Envia estado atual
                await ws.send_json({
                    "type": "init",
                    "sessions": [asdict(s) for s in self._sessions.values()],
                })
                # Mantém conexão viva
                while True:
                    data = await ws.receive_text()
                    msg = json.loads(data)
                    await self._handle_ws_message(ws, msg)
            except WebSocketDisconnect:
                self._websockets.remove(ws)
                logger.info("Professor desconectado")

        return app

    async def _handle_ws_message(self, ws: Any, msg: dict) -> None:
        """Trata mensagens do professor via WebSocket."""
        msg_type = msg.get("type")
        student_id = msg.get("student_id")

        if msg_type == "intervene" and student_id:
            # Professor intervém na sessão de um aluno
            session = self._sessions.get(student_id)
            if session:
                await ws.send_json({
                    "type": "intervention_sent",
                    "student_id": student_id,
                    "message": msg.get("message", ""),
                })
                logger.info("Intervenção do professor", student_id=student_id)

        elif msg_type == "pause" and student_id:
            session = self._sessions.get(student_id)
            if session:
                session.active = False
                await self._broadcast({"type": "session_paused", "student_id": student_id})

    async def _broadcast(self, data: dict) -> None:
        """Envia dados para todos os professores conectados."""
        disconnected = []
        for ws in self._websockets:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._websockets.remove(ws)

    def register_session(self, session: StudentSession) -> None:
        """Registra nova sessão de aluno."""
        self._sessions[session.student_id] = session
        asyncio.create_task(self._broadcast({
            "type": "session_start",
            "session": asdict(session),
        })) if self._websockets else None
        logger.info("Sessão registrada", student=session.student_name, task=session.task[:60])

    def update_session(self, student_id: str, **kwargs) -> None:
        """Atualiza estado de sessão de aluno."""
        session = self._sessions.get(student_id)
        if not session:
            return
        for k, v in kwargs.items():
            if hasattr(session, k):
                setattr(session, k, v)
        if session.steps_total > 0:
            session.completion_pct = session.steps_done / session.steps_total * 100

        if self._websockets:
            asyncio.create_task(self._broadcast({
                "type": "session_update",
                "session": asdict(session),
            }))

    def report_error(self, student_id: str, error: dict) -> None:
        """Reporta erro detectado em sessão de aluno."""
        session = self._sessions.get(student_id)
        if not session:
            return
        session.errors.append({**error, "timestamp": time.time()})
        if self._websockets:
            asyncio.create_task(self._broadcast({
                "type": "student_error",
                "student_id": student_id,
                "error": error,
            }))

    def _get_dashboard_html(self) -> str:
        return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NeoPilot — Dashboard do Professor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; }
        header {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        header h1 { font-size: 20px; color: #4fc3f7; }
        .badge {
            background: rgba(76,175,80,0.2);
            color: #81c784;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .dashboard { padding: 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
        .session-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 16px;
            transition: border-color 0.2s;
        }
        .session-card:hover { border-color: rgba(79,195,247,0.4); }
        .session-card.has-error { border-color: rgba(244,67,54,0.4); }
        .student-name { font-size: 16px; font-weight: 600; color: #4fc3f7; margin-bottom: 4px; }
        .task-text { font-size: 12px; color: #9e9e9e; margin-bottom: 12px; }
        .progress-bar {
            background: rgba(255,255,255,0.08);
            border-radius: 4px;
            height: 6px;
            margin-bottom: 8px;
            overflow: hidden;
        }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #4fc3f7, #81c784); transition: width 0.5s; }
        .stats { display: flex; gap: 12px; font-size: 11px; color: #9e9e9e; }
        .errors-section { margin-top: 10px; }
        .error-item {
            background: rgba(244,67,54,0.1);
            border-left: 3px solid #e57373;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 11px;
            color: #ef9a9a;
            margin-top: 4px;
        }
        .intervene-btn {
            margin-top: 10px;
            background: rgba(79,195,247,0.15);
            color: #4fc3f7;
            border: 1px solid rgba(79,195,247,0.3);
            border-radius: 6px;
            padding: 4px 12px;
            cursor: pointer;
            font-size: 12px;
        }
        .intervene-btn:hover { background: rgba(79,195,247,0.25); }
        #status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #1a1a2e;
            padding: 8px 24px;
            font-size: 12px;
            color: #9e9e9e;
            border-top: 1px solid rgba(255,255,255,0.08);
        }
        .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #81c784; margin-right: 4px; }
        .dot.disconnected { background: #e57373; }
    </style>
</head>
<body>
    <header>
        <h1>🎓 NeoPilot Professor Dashboard</h1>
        <span class="badge" id="active-count">0 alunos ativos</span>
    </header>
    <div class="dashboard" id="dashboard"></div>
    <div id="status-bar"><span class="dot disconnected" id="ws-dot"></span><span id="ws-status">Conectando...</span></div>

    <script>
    const ws = new WebSocket(`ws://${location.host}/ws`);
    const sessions = {};

    ws.onopen = () => {
        document.getElementById('ws-dot').className = 'dot';
        document.getElementById('ws-status').textContent = 'Conectado ao servidor';
    };
    ws.onclose = () => {
        document.getElementById('ws-dot').className = 'dot disconnected';
        document.getElementById('ws-status').textContent = 'Desconectado — tentando reconectar...';
        setTimeout(() => location.reload(), 3000);
    };
    ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'init') {
            msg.sessions.forEach(s => { sessions[s.student_id] = s; });
        } else if (msg.type === 'session_start') {
            sessions[msg.session.student_id] = msg.session;
        } else if (msg.type === 'session_update') {
            sessions[msg.session.student_id] = msg.session;
        } else if (msg.type === 'student_error') {
            const s = sessions[msg.student_id];
            if (s) s.errors = [...(s.errors || []), msg.error];
        }
        renderDashboard();
    };

    function renderDashboard() {
        const dash = document.getElementById('dashboard');
        const active = Object.values(sessions).filter(s => s.active).length;
        document.getElementById('active-count').textContent = `${active} alunos ativos`;

        dash.innerHTML = Object.values(sessions).map(s => `
            <div class="session-card ${s.errors?.length ? 'has-error' : ''}">
                <div class="student-name">${s.student_name}</div>
                <div class="task-text">${s.task}</div>
                <div class="progress-bar"><div class="progress-fill" style="width:${s.completion_pct}%"></div></div>
                <div class="stats">
                    <span>✅ ${s.steps_done}/${s.steps_total} passos</span>
                    <span>❌ ${s.errors?.length || 0} erros</span>
                    <span>${Math.round(s.completion_pct)}% concluído</span>
                </div>
                ${s.errors?.length ? `
                    <div class="errors-section">
                        ${s.errors.slice(-2).map(e => `<div class="error-item">${e.description || e.severity}</div>`).join('')}
                    </div>
                ` : ''}
                <button class="intervene-btn" onclick="intervene('${s.student_id}')">💬 Intervir</button>
            </div>
        `).join('');
    }

    function intervene(studentId) {
        const msg = prompt('Mensagem para o aluno:');
        if (msg) {
            ws.send(JSON.stringify({ type: 'intervene', student_id: studentId, message: msg }));
        }
    }

    renderDashboard();
    </script>
</body>
</html>"""

    async def start(self) -> None:
        """Inicia servidor FastAPI."""
        if not self._available:
            return
        try:
            import uvicorn
            app = self.create_app()
            config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
            server = uvicorn.Server(config)
            logger.info("Professor Dashboard iniciando", host=self.host, port=self.port)
            await server.serve()
        except ImportError:
            logger.warning("uvicorn não instalado, dashboard não iniciará")
        except Exception as e:
            logger.error("Dashboard falhou ao iniciar", error=str(e))
