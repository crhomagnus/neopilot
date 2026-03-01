"""Testes unitários — MemoryManager."""

import tempfile
import time
from pathlib import Path

import pytest

from neopilot.memory.manager import Episode, EpisodicMemory, MemoryManager


@pytest.fixture
def tmp_db(tmp_path):
    return EpisodicMemory(tmp_path / "test.db")


@pytest.fixture
def manager(tmp_path):
    return MemoryManager(base_dir=tmp_path)


def test_save_and_retrieve_episode(tmp_db):
    ep = Episode(
        task="Criar planilha de vendas",
        steps=[{"action": "click", "target": "LibreOffice Calc"}],
        result="Planilha criada com sucesso",
        success=True,
        app_name="libreoffice",
    )
    ep_id = tmp_db.save(ep)
    assert ep_id > 0

    recent = tmp_db.get_recent(limit=5)
    assert len(recent) == 1
    assert recent[0]["task"] == "Criar planilha de vendas"
    assert recent[0]["success"] == 1


def test_search_similar_episodes(tmp_db):
    episodes = [
        Episode(task="Abrir planilha de vendas", steps=[], result="OK", success=True),
        Episode(task="Criar documento Word", steps=[], result="OK", success=True),
        Episode(task="Navegar para site de compras", steps=[], result="Falhou", success=False),
    ]
    for ep in episodes:
        tmp_db.save(ep)

    results = tmp_db.search_similar(["planilha"], limit=5)
    assert len(results) >= 1
    assert any("planilha" in r["task"].lower() for r in results)


def test_stats(tmp_db):
    for i in range(5):
        tmp_db.save(Episode(
            task=f"Tarefa {i}",
            steps=[],
            result="OK",
            success=(i % 2 == 0),
        ))

    stats = tmp_db.stats()
    assert stats["total"] == 5
    assert stats["success"] == 3
    assert stats["failure"] == 2


def test_memory_manager_working_memory(manager):
    manager.add_to_working_memory({"step": 1, "action": "click", "target": "botão OK"})
    manager.add_to_working_memory({"step": 2, "action": "type", "text": "Olá mundo"})

    wm = manager.get_working_memory()
    assert len(wm) == 2
    assert wm[0]["step"] == 1

    manager.clear_working_memory()
    assert len(manager.get_working_memory()) == 0


def test_remember_episode_integration(manager):
    ep = Episode(
        task="Criar relatório mensal",
        steps=[
            {"action": "click", "target": "Novo Documento"},
            {"action": "type", "text": "Relatório Janeiro 2026"},
        ],
        result="Relatório criado",
        success=True,
        app_name="libreoffice",
        session_id="sess-001",
    )
    ep_id = manager.remember_episode(ep)
    assert ep_id > 0

    stats = manager.stats()
    assert stats["episodic"]["total"] == 1
    assert stats["episodic"]["success"] == 1


def test_working_memory_max_size(manager):
    """Testa que working memory respeita tamanho máximo."""
    for i in range(25):
        manager.add_to_working_memory({"i": i})

    wm = manager.get_working_memory()
    assert len(wm) <= 20
    # Deve ter os itens mais recentes
    assert wm[-1]["i"] == 24


def test_format_context_empty(manager):
    """Sem episódios, formato de contexto deve ser string vazia."""
    ctx = manager.format_context_for_llm("tarefa qualquer")
    assert ctx == "" or "Memória" in ctx
