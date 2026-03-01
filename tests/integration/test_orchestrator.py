"""
Testes de integração do NeoPilot Orchestrator com LLM mockado.
Valida o fluxo ReAct completo sem chamadas reais à API.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from neopilot.core.agent_graph import NeoPilotOrchestrator, build_agent_graph, NeoPilotState
from neopilot.memory.manager import MemoryManager


@pytest.fixture
def mock_llm():
    """LLM que retorna respostas JSON fixas para cada tipo de nó."""
    llm = MagicMock()

    # Resposta do planner
    plan_response = MagicMock()
    plan_response.content = json.dumps({
        "steps": [
            {"step": 1, "action": "done", "target": "tarefa simples", "description": "Concluir diretamente"}
        ]
    })

    # Resposta do reasoner
    reason_response = MagicMock()
    reason_response.content = json.dumps({
        "action_type": "done",
        "target": "concluído",
        "value": "",
        "requires_confirmation": False,
        "reasoning": "Tarefa simples, sem ação necessária"
    })

    # ainvoke retorna plan na primeira chamada, reason nas seguintes
    call_count = [0]

    async def ainvoke_side_effect(messages):
        call_count[0] += 1
        if call_count[0] == 1:
            return plan_response
        return reason_response

    llm.ainvoke = AsyncMock(side_effect=ainvoke_side_effect)
    return llm


@pytest.fixture
def mock_context_builder():
    cb = MagicMock()
    ctx = MagicMock()
    ctx.active_window = {"name": "Terminal", "url": ""}
    ctx.accessibility_tree = {"children": []}
    ctx.ocr_text = ""
    cb.build.return_value = ctx
    return cb


@pytest.fixture
def mock_desktop_agent():
    agent = MagicMock()
    result = MagicMock()
    result.success = True
    result.method = "atspi"
    result.error = None
    agent.execute_action = AsyncMock(return_value=result)
    return agent


@pytest.fixture
def mock_web_agent():
    agent = MagicMock()
    result = MagicMock()
    result.success = True
    result.method = "playwright"
    result.error = None
    agent.navigate = AsyncMock(return_value=result)
    agent.execute_action = AsyncMock(return_value=result)
    return agent


@pytest.fixture
def mock_lo_agent():
    agent = MagicMock()
    result = MagicMock()
    result.success = True
    result.method = "uno"
    result.file_path = "/tmp/test.odt"
    agent.create_writer_document.return_value = result
    agent.create_calc_spreadsheet.return_value = result
    return agent


@pytest.fixture
def memory(tmp_path):
    return MemoryManager(base_dir=tmp_path / "memory")


@pytest.fixture
def audit(tmp_path):
    from neopilot.core.logger import AuditLogger
    return AuditLogger(tmp_path / "audit.jsonl")


@pytest.mark.asyncio
async def test_full_react_loop_simple_task(
    mock_llm, mock_context_builder, mock_desktop_agent,
    mock_web_agent, mock_lo_agent, memory, audit
):
    """Testa loop ReAct completo com tarefa simples (done em 1 passo)."""
    graph = build_agent_graph(
        llm=mock_llm,
        desktop_agent=mock_desktop_agent,
        web_agent=mock_web_agent,
        lo_agent=mock_lo_agent,
        memory=memory,
        context_builder=mock_context_builder,
        audit=audit,
    )

    initial_state: NeoPilotState = {
        "messages": [],
        "task": "Tarefa de teste simples",
        "plan": [],
        "current_step": 0,
        "observation": "",
        "action_history": [],
        "active_app": "",
        "error_count": 0,
        "requires_confirmation": False,
        "user_approved": True,
        "session_id": "test-001",
        "professor_mode": False,
        "professor_errors": [],
        "done": False,
        "result": "",
    }

    final_state = await graph.ainvoke(initial_state)

    assert final_state["done"] is True
    assert len(final_state["plan"]) > 0
    assert mock_llm.ainvoke.call_count >= 1


@pytest.mark.asyncio
async def test_memory_integration(memory):
    """Testa que episódios são salvos e recuperados corretamente."""
    from neopilot.memory.manager import Episode

    ep = Episode(
        task="Criar relatório no LibreOffice Writer",
        steps=[
            {"action": "click", "target": "LibreOffice Writer"},
            {"action": "type", "text": "Relatório mensal"},
        ],
        result="Documento criado com sucesso",
        success=True,
        app_name="libreoffice",
        session_id="test-session",
    )

    ep_id = memory.remember_episode(ep)
    assert ep_id > 0

    stats = memory.stats()
    assert stats["episodic"]["total"] == 1
    assert stats["episodic"]["success"] == 1

    similar = memory.recall_similar("relatório LibreOffice Writer")
    # Pode vir de busca semântica ou keyword
    assert isinstance(similar, list)


@pytest.mark.asyncio
async def test_orchestrator_initialization_with_mock():
    """Testa inicialização do NeoPilotOrchestrator com LLM mockado."""
    orch = NeoPilotOrchestrator()

    with patch.object(orch, '_build_llm') as mock_build:
        mock_build.return_value = MagicMock()

        with patch('neopilot.agents.desktop_agent.DesktopAgent'):
            with patch('neopilot.agents.web_agent.WebAgent') as MockWebAgent:
                MockWebAgent.return_value.start = AsyncMock()
                with patch('neopilot.integrations.libreoffice.lo_agent.LibreOfficeAgent'):
                    with patch('neopilot.perception.context_builder.ContextBuilder'):
                        await orch.initialize()
                        assert orch._initialized


@pytest.mark.asyncio
async def test_professor_mode_flag(
    mock_llm, mock_context_builder, mock_desktop_agent,
    mock_web_agent, mock_lo_agent, memory, audit
):
    """Testa que modo professor é propagado no estado."""
    graph = build_agent_graph(
        llm=mock_llm,
        desktop_agent=mock_desktop_agent,
        web_agent=mock_web_agent,
        lo_agent=mock_lo_agent,
        memory=memory,
        context_builder=mock_context_builder,
        audit=audit,
    )

    initial_state: NeoPilotState = {
        "messages": [],
        "task": "Aula de LibreOffice Calc",
        "plan": [],
        "current_step": 0,
        "observation": "",
        "action_history": [],
        "active_app": "",
        "error_count": 0,
        "requires_confirmation": False,
        "user_approved": True,
        "session_id": "prof-001",
        "professor_mode": True,  # ← modo professor ativo
        "professor_errors": [],
        "done": False,
        "result": "",
    }

    final_state = await graph.ainvoke(initial_state)
    assert final_state["professor_mode"] is True
    assert final_state["done"] is True


@pytest.mark.asyncio
async def test_sandbox_human_gate():
    """Testa HumanInTheLoopGate com aprovação e negação."""
    from neopilot.security.sandbox import HumanInTheLoopGate

    gate = HumanInTheLoopGate()

    # Testa que ação sensível é detectada
    assert gate.is_sensitive("delete_file")
    assert gate.is_sensitive("sudo apt-get remove")
    assert not gate.is_sensitive("read_file")
    assert not gate.is_sensitive("navigate")

    # Testa aprovação assíncrona
    async def approve_after_delay():
        await asyncio.sleep(0.05)
        gate.approve("test-action-1")

    asyncio.create_task(approve_after_delay())
    result = await gate.request_approval("test-action-1", "Deletar arquivo test.txt", timeout_s=2.0)
    assert result is True

    # Testa negação
    async def deny_after_delay():
        await asyncio.sleep(0.05)
        gate.deny("test-action-2")

    asyncio.create_task(deny_after_delay())
    result = await gate.request_approval("test-action-2", "Executar sudo rm -rf", timeout_s=2.0)
    assert result is False
