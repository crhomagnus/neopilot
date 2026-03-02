"""
NeoPilot Session Manager
Manages teaching session lifecycle, state transitions, and Claude conversation context.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.session import (
    ActionLog,
    ActionType,
    Session,
    SessionState,
    StudentState,
)
from backend.app.models.schemas import (
    ActionCommand,
    OverlayCommand,
    SessionPhase,
    TeachingResponse,
)
from backend.app.services.claude_client import ClaudeClient

logger = structlog.get_logger(__name__)


class SessionManager:
    """
    Manages teaching sessions: creation, observation processing,
    action result handling, and Claude conversation flow.
    """

    def __init__(self, claude: ClaudeClient) -> None:
        self.claude = claude
        # In-memory session cache for conversation history
        # In production, this would be backed by Redis
        self._conversations: dict[str, list[dict[str, Any]]] = {}
        self._session_metadata: dict[str, dict[str, Any]] = {}

    async def create_session(
        self,
        db: AsyncSession,
        app_id: str,
        task_description: str,
        user_context: dict[str, Any],
        language: str = "pt-BR",
    ) -> tuple[Session, TeachingResponse]:
        """
        Create a new teaching session and get the initial teaching plan from Claude.
        """
        session = Session(
            id=str(uuid.uuid4()),
            app_id=app_id,
            task_description=task_description,
            state=SessionState.INITIALIZING,
            user_context=user_context,
        )
        db.add(session)

        # Create student state tracker
        student_state = StudentState(
            session_id=session.id,
            lesson_id=f"{app_id}:{task_description[:50]}",
            current_phase="demo",
        )
        db.add(student_state)
        await db.flush()

        # Initialize conversation with Claude
        initial_prompt = (
            f"Nova sessão de ensino iniciada.\n\n"
            f"**Aplicativo**: {app_id}\n"
            f"**Tarefa**: {task_description}\n"
            f"**Idioma**: {language}\n"
            f"**Contexto do estudante**: {user_context}\n\n"
            f"Por favor:\n"
            f"1. Cumprimente o estudante.\n"
            f"2. Explique brevemente o que vocês vão aprender.\n"
            f"3. Peça um screenshot para ver o estado atual da tela.\n"
            f"4. Prepare o plano de ensino (não execute ações ainda, apenas planeje)."
        )

        result = self.claude.chat(
            conversation_history=[],
            user_text=initial_prompt,
        )

        # Store conversation in memory
        self._conversations[session.id] = result["conversation"]
        self._session_metadata[session.id] = {
            "app_id": app_id,
            "task": task_description,
            "language": language,
        }

        # Update session state
        session.state = SessionState.ACTIVE
        session.total_tokens_used = (
            result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        )
        session.claude_conversation = result["conversation"]

        # Parse initial response
        actions, overlays = self._parse_tool_calls(result.get("tool_calls", []))

        response = TeachingResponse(
            session_id=session.id,
            message=result["text"],
            actions=actions,
            overlays=overlays,
            phase=SessionPhase.DEMO,
            progress_pct=0.0,
        )

        await db.commit()

        logger.info(
            "session_created",
            session_id=session.id,
            app_id=app_id,
            task=task_description[:60],
            initial_tokens=session.total_tokens_used,
        )

        return session, response

    async def process_observation(
        self,
        db: AsyncSession,
        session_id: str,
        screenshot_b64: str,
        text: Optional[str] = None,
        app_metadata: Optional[dict[str, Any]] = None,
    ) -> TeachingResponse:
        """
        Process a new observation (screenshot + optional text) from the client.
        Sends to Claude and returns the teaching response.
        """
        session = await self._get_session(db, session_id)
        conversation = self._conversations.get(session_id, [])

        # Build context text
        context_parts = []
        if text:
            context_parts.append(f"**Estudante disse**: {text}")
        if app_metadata:
            context_parts.append(f"**Metadados do app**: {app_metadata}")

        user_text = "\n".join(context_parts) if context_parts else None

        # Call Claude with screenshot
        result = self.claude.chat(
            conversation_history=conversation,
            screenshot_b64=screenshot_b64,
            user_text=user_text,
        )

        # Update conversation
        self._conversations[session_id] = result["conversation"]

        # Track tokens
        new_tokens = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        session.total_tokens_used += new_tokens
        session.current_step += 1
        session.claude_conversation = result["conversation"]

        # Handle tool calls → convert to actions/overlays
        actions, overlays = self._parse_tool_calls(result.get("tool_calls", []))

        # Process tool call loop if Claude wants to use tools
        if result["stop_reason"] == "tool_use" and result["tool_calls"]:
            response = await self._handle_tool_loop(
                db, session, result, actions, overlays
            )
        else:
            response = TeachingResponse(
                session_id=session_id,
                message=result["text"],
                actions=actions,
                overlays=overlays,
                phase=self._get_phase(session),
                progress_pct=self._estimate_progress(session),
            )

        # Log actions
        for action in actions:
            log = ActionLog(
                session_id=session_id,
                step=session.current_step,
                action_type=self._map_action_type(action.type),
                payload=action.params,
            )
            db.add(log)

        await db.commit()
        return response

    async def process_action_result(
        self,
        db: AsyncSession,
        session_id: str,
        action_id: str,
        success: bool,
        screenshot_after_b64: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> TeachingResponse:
        """
        Process the result of an action executed by the client.
        Reports back to Claude for evaluation and next steps.
        """
        session = await self._get_session(db, session_id)
        conversation = self._conversations.get(session_id, [])

        # Build result text for Claude
        result_text = f"Resultado da ação '{action_id}': "
        if success:
            result_text += "SUCESSO."
        else:
            result_text += f"FALHOU. Erro: {error_message or 'desconhecido'}"

        # Send to Claude with the post-action screenshot
        result = self.claude.chat(
            conversation_history=conversation,
            screenshot_b64=screenshot_after_b64,
            user_text=result_text,
        )

        self._conversations[session_id] = result["conversation"]

        new_tokens = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        session.total_tokens_used += new_tokens

        actions, overlays = self._parse_tool_calls(result.get("tool_calls", []))

        # Update student state
        student = await self._get_student_state(db, session_id)
        if student:
            if success:
                student.correct_actions += 1
            else:
                student.errors_made += 1
                session.error_count += 1

        if result["stop_reason"] == "tool_use" and result["tool_calls"]:
            response = await self._handle_tool_loop(
                db, session, result, actions, overlays
            )
        else:
            response = TeachingResponse(
                session_id=session_id,
                message=result["text"],
                actions=actions,
                overlays=overlays,
                phase=self._get_phase(session),
                progress_pct=self._estimate_progress(session),
            )

        await db.commit()
        return response

    async def _handle_tool_loop(
        self,
        db: AsyncSession,
        session: Session,
        initial_result: dict[str, Any],
        actions: list[ActionCommand],
        overlays: list[OverlayCommand],
    ) -> TeachingResponse:
        """
        Handle cases where Claude makes tool calls that can be resolved
        server-side (e.g., set_teaching_phase, clear_overlays).
        ACI actions (click, type, etc.) are forwarded to the client.
        """
        server_tools = {"set_teaching_phase", "evaluate_action", "clear_overlays"}
        result = initial_result
        all_text_parts = [result["text"]] if result["text"] else []

        max_iterations = 5
        for _ in range(max_iterations):
            if result["stop_reason"] != "tool_use":
                break

            # Check if any tool calls are server-resolvable
            tool_results = []
            for tc in result["tool_calls"]:
                if tc["name"] in server_tools:
                    tr_content = await self._execute_server_tool(
                        db, session, tc["name"], tc["input"]
                    )
                    tool_results.append({
                        "tool_use_id": tc["id"],
                        "content": tr_content,
                    })

            if not tool_results:
                # All tool calls are client-side, stop the loop
                break

            # Submit server tool results back to Claude
            result = self.claude.submit_tool_results(
                conversation_history=result["conversation"],
                tool_results=tool_results,
            )
            self._conversations[session.id] = result["conversation"]

            new_tokens = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
            session.total_tokens_used += new_tokens

            if result["text"]:
                all_text_parts.append(result["text"])

            new_actions, new_overlays = self._parse_tool_calls(result.get("tool_calls", []))
            actions.extend(new_actions)
            overlays.extend(new_overlays)

        return TeachingResponse(
            session_id=session.id,
            message="\n\n".join(all_text_parts),
            actions=actions,
            overlays=overlays,
            phase=self._get_phase(session),
            progress_pct=self._estimate_progress(session),
        )

    async def _execute_server_tool(
        self,
        db: AsyncSession,
        session: Session,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> str:
        """Execute a tool that can be resolved on the server."""
        if tool_name == "set_teaching_phase":
            phase = tool_input.get("phase", "demo")
            student = await self._get_student_state(db, session.id)
            if student:
                student.current_phase = phase
            session.state = SessionState(phase) if phase in SessionState.__members__ else SessionState.ACTIVE
            return f"Fase de ensino alterada para '{phase}'."

        elif tool_name == "evaluate_action":
            return "Avaliação registrada. Aguardando próximo screenshot para verificação."

        elif tool_name == "clear_overlays":
            return "Todos os overlays foram removidos."

        return "Tool executed."

    def _parse_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> tuple[list[ActionCommand], list[OverlayCommand]]:
        """Parse Claude's tool calls into ActionCommands and OverlayCommands."""
        actions: list[ActionCommand] = []
        overlays: list[OverlayCommand] = []

        aci_tools = {"click", "type_text", "hotkey", "mouse_move", "scroll", "drag", "wait", "request_screenshot", "speak", "ask_student"}
        overlay_tools = {"overlay_arrow", "overlay_highlight", "overlay_text", "clear_overlays"}

        for tc in tool_calls:
            if tc["name"] in aci_tools:
                actions.append(ActionCommand(
                    id=tc["id"],
                    type=tc["name"],
                    params=tc["input"],
                    description=f"Execute {tc['name']}",
                ))
            elif tc["name"] in overlay_tools:
                overlays.append(OverlayCommand(
                    type=tc["name"],
                    params=tc["input"],
                    duration_ms=tc["input"].get("duration_ms", 3000),
                ))

        return actions, overlays

    async def _get_session(self, db: AsyncSession, session_id: str) -> Session:
        """Get session by ID or raise."""
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        return session

    async def _get_student_state(self, db: AsyncSession, session_id: str) -> Optional[StudentState]:
        """Get student state for a session."""
        result = await db.execute(
            select(StudentState).where(StudentState.session_id == session_id)
        )
        return result.scalar_one_or_none()

    def _get_phase(self, session: Session) -> SessionPhase:
        """Map session state to teaching phase."""
        mapping = {
            SessionState.DEMO: SessionPhase.DEMO,
            SessionState.EXERCISE: SessionPhase.EXERCISE,
            SessionState.ASSESSMENT: SessionPhase.ASSESSMENT,
        }
        return mapping.get(session.state, SessionPhase.DEMO)

    def _estimate_progress(self, session: Session) -> float:
        """Rough progress estimation based on steps completed."""
        # Simple heuristic; will be improved with Teaching Engine
        if session.current_step == 0:
            return 0.0
        return min(session.current_step / 20, 1.0) * 100

    def _map_action_type(self, action_type_str: str) -> ActionType:
        """Map string action type to ActionType enum."""
        mapping = {
            "click": ActionType.CLICK,
            "type_text": ActionType.TYPE_TEXT,
            "hotkey": ActionType.HOTKEY,
            "mouse_move": ActionType.CLICK,
            "scroll": ActionType.CLICK,
            "drag": ActionType.CLICK,
            "wait": ActionType.WAIT,
            "request_screenshot": ActionType.SCREENSHOT,
            "speak": ActionType.SPEAK,
            "ask_student": ActionType.ASK,
        }
        return mapping.get(action_type_str, ActionType.CLICK)

    async def get_session_status(self, db: AsyncSession, session_id: str) -> dict[str, Any]:
        """Get detailed session status."""
        session = await self._get_session(db, session_id)
        student = await self._get_student_state(db, session_id)

        return {
            "session_id": session.id,
            "state": session.state.value,
            "current_step": session.current_step,
            "total_tokens_used": session.total_tokens_used,
            "total_cost_usd": session.total_cost_usd,
            "error_count": session.error_count,
            "progress_pct": self._estimate_progress(session),
            "student": {
                "correct_actions": student.correct_actions if student else 0,
                "errors_made": student.errors_made if student else 0,
                "current_phase": student.current_phase if student else "demo",
                "hints_given": student.hints_given if student else 0,
            } if student else None,
            "claude_metrics": self.claude.get_metrics(),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }
