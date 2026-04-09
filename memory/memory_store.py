"""
memory/memory_store.py
Persistent ChromaDB-backed memory for SmithAgentic agents.

All entries are tagged with a session_id so memories from different runs
can be distinguished. The store persists to disk at memory/chroma/.

Tools exported:
    MemoryStoreTool  — save a key insight to memory
    MemoryQueryTool  — retrieve relevant memories for a topic
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_HERE = Path(__file__).resolve().parent
_DEFAULT_PERSIST = _HERE / "chroma"

# ── Lazy ChromaDB init ────────────────────────────────────────────────────────

_client = None
_collection = None


def _get_collection(persist_dir: Path | str | None = None, collection_name: str = "smith_agentic_memory"):
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
    except ImportError:
        return None  # memory disabled gracefully if chromadb not installed

    persist_path = str(persist_dir or _DEFAULT_PERSIST)
    Path(persist_path).mkdir(parents=True, exist_ok=True)
    _client = chromadb.PersistentClient(path=persist_path)
    _collection = _client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


# ── Session ID (new ID per process run) ──────────────────────────────────────

_SESSION_ID = str(uuid.uuid4())[:8]


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class _StoreInput(BaseModel):
    content: str = Field(description="The insight, fact, or result to remember.")
    topic: str = Field(description="A short label for this memory (e.g. 'plc design', 'react components').")


class _QueryInput(BaseModel):
    query: str = Field(description="Natural language query to find relevant memories.")
    n_results: int = Field(default=5, description="How many memories to retrieve (default: 5).")


# ── Tools ─────────────────────────────────────────────────────────────────────

class MemoryStoreTool(BaseTool):
    name: str = "Store Memory"
    description: str = (
        "Save an important insight, decision, or result to persistent memory. "
        "Use after research findings, key decisions, or completed deliverables. "
        "Stored memories persist across sessions and can be retrieved by future agents."
    )
    args_schema: Type[BaseModel] = _StoreInput

    persist_dir: str = str(_DEFAULT_PERSIST)
    collection_name: str = "smith_agentic_memory"

    def _run(self, content: str, topic: str) -> str:
        col = _get_collection(self.persist_dir, self.collection_name)
        if col is None:
            return "Memory disabled — chromadb not installed. Install with: pip install chromadb"

        entry_id = f"{_SESSION_ID}-{uuid.uuid4().hex[:8]}"
        col.add(
            documents=[content],
            metadatas=[{"topic": topic, "session": _SESSION_ID}],
            ids=[entry_id],
        )
        return f"Stored to memory (id={entry_id}, topic='{topic}', session={_SESSION_ID})."


class MemoryQueryTool(BaseTool):
    name: str = "Query Memory"
    description: str = (
        "Search persistent memory for relevant past insights, decisions, or results. "
        "Use at the start of a task to check if similar work has been done before. "
        "Returns the most relevant stored memories for the given query."
    )
    args_schema: Type[BaseModel] = _QueryInput

    persist_dir: str = str(_DEFAULT_PERSIST)
    collection_name: str = "smith_agentic_memory"

    def _run(self, query: str, n_results: int = 5) -> str:
        col = _get_collection(self.persist_dir, self.collection_name)
        if col is None:
            return "Memory disabled — chromadb not installed."

        count = col.count()
        if count == 0:
            return "Memory is empty — no past entries found."

        results = col.query(
            query_texts=[query],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        if not docs:
            return "No relevant memories found."

        lines = [f"Found {len(docs)} relevant memory entries:\n"]
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), 1):
            score = round(1 - dist, 3)
            lines.append(
                f"[{i}] topic={meta.get('topic','?')} session={meta.get('session','?')} relevance={score}\n"
                f"    {doc[:300]}{'...' if len(doc) > 300 else ''}"
            )
        return "\n".join(lines)


# ── Factory (called by crews to inject configured tools) ─────────────────────

def create_memory_tools(config: dict) -> tuple[MemoryStoreTool, MemoryQueryTool]:
    """Return (MemoryStoreTool, MemoryQueryTool) configured from config dict."""
    mem_cfg = config.get("memory", {})
    if not mem_cfg.get("enabled", True):
        # Return dummy tools that do nothing
        return MemoryStoreTool(), MemoryQueryTool()

    persist_dir = str(
        Path(__file__).resolve().parent.parent / mem_cfg.get("persist_dir", "memory/chroma")
    )
    collection_name = mem_cfg.get("collection", "smith_agentic_memory")
    return (
        MemoryStoreTool(persist_dir=persist_dir, collection_name=collection_name),
        MemoryQueryTool(persist_dir=persist_dir, collection_name=collection_name),
    )
