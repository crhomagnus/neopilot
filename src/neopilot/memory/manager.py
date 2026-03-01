"""
NeoPilot Memory Manager
Memória episódica (SQLite) + semântica (ChromaDB) para o agente.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from neopilot.core.logger import get_logger

logger = get_logger("memory")


@dataclass
class Episode:
    """Um episódio de interação do agente."""
    task: str
    steps: list[dict]
    result: str
    success: bool
    app_name: Optional[str] = None
    duration_s: float = 0.0
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""


@dataclass
class MemorySearchResult:
    episode_id: int
    task: str
    result: str
    success: bool
    similarity: float
    steps_summary: str


class EpisodicMemory:
    """Memória episódica baseada em SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    result TEXT,
                    success INTEGER NOT NULL,
                    app_name TEXT,
                    duration_s REAL DEFAULT 0,
                    timestamp REAL NOT NULL,
                    session_id TEXT DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_app ON episodes(app_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_success ON episodes(success)")
            conn.commit()

    def save(self, episode: Episode) -> int:
        """Salva episódio e retorna ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO episodes
                   (task, steps_json, result, success, app_name, duration_s, timestamp, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    episode.task,
                    json.dumps(episode.steps),
                    episode.result,
                    int(episode.success),
                    episode.app_name,
                    episode.duration_s,
                    episode.timestamp,
                    episode.session_id,
                ),
            )
            conn.commit()
            episode_id = cursor.lastrowid
            logger.debug("Episódio salvo", id=episode_id, task=episode.task[:60])
            return episode_id

    def get_recent(self, limit: int = 10, app_name: Optional[str] = None) -> list[dict]:
        """Retorna episódios recentes, opcionalmente filtrados por app."""
        query = "SELECT * FROM episodes"
        params: list[Any] = []
        if app_name:
            query += " WHERE app_name = ?"
            params.append(app_name)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def search_similar(self, task_keywords: list[str], limit: int = 5) -> list[dict]:
        """Busca episódios com keywords similares (busca simples por LIKE)."""
        if not task_keywords:
            return []

        conditions = " OR ".join(["task LIKE ?" for _ in task_keywords])
        params = [f"%{kw}%" for kw in task_keywords] + [limit]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM episodes WHERE {conditions} ORDER BY success DESC, timestamp DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def get_success_patterns(self, app_name: str) -> list[dict]:
        """Retorna padrões bem-sucedidos para um aplicativo."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes WHERE app_name = ? AND success = 1 ORDER BY timestamp DESC LIMIT 20",
                (app_name,),
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            success = conn.execute("SELECT COUNT(*) FROM episodes WHERE success=1").fetchone()[0]
            return {"total": total, "success": success, "failure": total - success}


class SemanticMemory:
    """Memória semântica baseada em ChromaDB para busca por similaridade vetorial."""

    def __init__(self, persist_dir: Path):
        self.persist_dir = persist_dir
        self._collection = None
        self._available = False
        self._init()

    def _init(self) -> None:
        try:
            import chromadb
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = client.get_or_create_collection(
                name="neopilot_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info("ChromaDB inicializado", persist_dir=str(self.persist_dir))
        except ImportError:
            logger.warning("ChromaDB não disponível, memória semântica desabilitada")
        except Exception as e:
            logger.error("Falha ao inicializar ChromaDB", error=str(e))

    def add(self, doc_id: str, text: str, metadata: Optional[dict] = None) -> None:
        """Adiciona documento à memória semântica."""
        if not self._available or not self._collection:
            return
        try:
            self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata or {}],
            )
        except Exception as e:
            logger.error("Falha ao adicionar ao ChromaDB", error=str(e))

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Busca documentos similares à query."""
        if not self._available or not self._collection:
            return []
        try:
            count = self._collection.count()
            if count == 0:
                return []
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
            )
            if not results["documents"]:
                return []
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]
            return [
                {"text": d, "metadata": m, "distance": dist}
                for d, m, dist in zip(docs, metas, distances)
            ]
        except Exception as e:
            logger.error("Falha ao buscar no ChromaDB", error=str(e))
            return []

    def add_episode_summary(self, episode_id: int, episode: Episode) -> None:
        """Adiciona resumo de episódio à memória semântica."""
        steps_text = "; ".join(
            f"{s.get('action', '')} em {s.get('target', '')}"
            for s in episode.steps[:5]
        )
        text = (
            f"Tarefa: {episode.task}. "
            f"App: {episode.app_name or 'desconhecido'}. "
            f"Passos: {steps_text}. "
            f"Resultado: {episode.result}. "
            f"Sucesso: {episode.success}"
        )
        self.add(
            doc_id=f"episode_{episode_id}",
            text=text,
            metadata={
                "episode_id": episode_id,
                "app": episode.app_name or "",
                "success": str(episode.success),
            },
        )


class MemoryManager:
    """
    Gerenciador unificado de memória do NeoPilot.
    Combina memória episódica (SQLite) e semântica (ChromaDB).
    """

    def __init__(self, base_dir: Optional[Path] = None):
        base = base_dir or Path.home() / ".neopilot" / "memory"
        self.episodic = EpisodicMemory(base / "episodes.db")
        self.semantic = SemanticMemory(base / "chroma")
        self._working_memory: list[dict] = []  # Contexto imediato da sessão
        self._max_working = 20

    def remember_episode(self, episode: Episode) -> int:
        """Salva episódio em memória episódica + semântica."""
        ep_id = self.episodic.save(episode)
        self.semantic.add_episode_summary(ep_id, episode)
        return ep_id

    def recall_similar(self, task: str, n: int = 3) -> list[dict]:
        """Recupera episódios similares por busca semântica + palavra-chave."""
        semantic_results = self.semantic.search(task, n_results=n)
        if semantic_results:
            return semantic_results

        # Fallback: busca por palavras-chave
        keywords = [w for w in task.split() if len(w) > 3]
        return self.episodic.search_similar(keywords, limit=n)

    def recall_app_patterns(self, app_name: str) -> list[dict]:
        """Retorna padrões de sucesso para um app específico."""
        return self.episodic.get_success_patterns(app_name)

    def add_to_working_memory(self, entry: dict) -> None:
        """Adiciona ao contexto imediato (janela deslizante)."""
        self._working_memory.append(entry)
        if len(self._working_memory) > self._max_working:
            self._working_memory.pop(0)

    def get_working_memory(self) -> list[dict]:
        return list(self._working_memory)

    def clear_working_memory(self) -> None:
        self._working_memory.clear()

    def format_context_for_llm(self, task: str) -> str:
        """Formata contexto de memória para inclusão no prompt do LLM."""
        similar = self.recall_similar(task, n=3)
        if not similar:
            return ""

        lines = ["## Memória Relevante\n"]
        for i, ep in enumerate(similar[:3], 1):
            text = ep.get("text") or ep.get("task", "")
            success = ep.get("metadata", {}).get("success", "?")
            lines.append(f"{i}. {text[:200]} [sucesso={success}]")

        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "episodic": self.episodic.stats(),
            "working_memory_size": len(self._working_memory),
            "semantic_available": self.semantic._available,
        }
