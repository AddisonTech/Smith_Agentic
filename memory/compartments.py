"""
memory/compartments.py
MIRIX 6-compartment memory — extends ChromaDB persistent storage into structured compartments.

Compartments:
  core            — fundamental agent identity and standing instructions
  episodic        — per-run events and task outcomes
  semantic        — factual knowledge and research findings
  procedural      — patterns, workflows, and how-to knowledge
  resource        — file paths, URLs, and external references
  knowledge_vault — curated high-value insights across runs
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_HERE = Path(__file__).resolve().parent
_DEFAULT_PERSIST = _HERE / "chroma"
_COMPARTMENTS = ["core", "episodic", "semantic", "procedural", "resource", "knowledge_vault"]

_SESSION_ID = str(uuid.uuid4())[:8]
_clients: dict[str, object] = {}
_collections: dict[str, object] = {}


def _get_compartment_collection(compartment: str, persist_dir: Path | str | None = None):
    global _clients, _collections
    key = f"{persist_dir}:{compartment}"
    if key in _collections:
        return _collections[key]
    try:
        import chromadb
    except ImportError:
        return None

    persist_path = str(persist_dir or _DEFAULT_PERSIST)
    Path(persist_path).mkdir(parents=True, exist_ok=True)
    if persist_path not in _clients:
        _clients[persist_path] = chromadb.PersistentClient(path=persist_path)
    client = _clients[persist_path]
    col = client.get_or_create_collection(
        name=f"smith_{compartment}",
        metadata={"hnsw:space": "cosine"},
    )
    _collections[key] = col
    return col


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class _CompStoreInput(BaseModel):
    content: str = Field(description="The insight, fact, or result to remember.")
    topic: str = Field(
        description="A short label for this memory (e.g. 'plc design', 'api endpoint')."
    )
    compartment: str = Field(
        default="episodic",
        description=(
            f"Memory compartment to store in. One of: {', '.join(_COMPARTMENTS)}. "
            "Default is 'episodic'. Use 'semantic' for factual knowledge, 'procedural' for "
            "workflows, 'resource' for file/URL references, 'knowledge_vault' for curated insights."
        ),
    )


class _CompQueryInput(BaseModel):
    query: str = Field(description="Natural language query to find relevant memories.")
    compartment: str = Field(
        default="episodic",
        description=(
            f"Compartment to search. One of: {', '.join(_COMPARTMENTS)}, or 'all' to search all. "
            "Default is 'episodic'."
        ),
    )
    n_results: int = Field(default=5, description="How many memories to retrieve (default: 5).")


# ── Tools ─────────────────────────────────────────────────────────────────────

class CompartmentStoreTool(BaseTool):
    name: str = "Store Compartment Memory"
    description: str = (
        "Save a memory entry to a specific MIRIX compartment (core, episodic, semantic, "
        "procedural, resource, knowledge_vault). Use for structured long-term storage. "
        "Stored memories persist across sessions."
    )
    args_schema: Type[BaseModel] = _CompStoreInput

    persist_dir: str = str(_DEFAULT_PERSIST)

    def _run(self, content: str, topic: str, compartment: str = "episodic") -> str:
        if compartment not in _COMPARTMENTS:
            return (
                f"Error: '{compartment}' is not a valid compartment. "
                f"Use one of: {', '.join(_COMPARTMENTS)}"
            )
        col = _get_compartment_collection(compartment, self.persist_dir)
        if col is None:
            return "Memory disabled — chromadb not installed. Install with: pip install chromadb"
        entry_id = f"{_SESSION_ID}-{uuid.uuid4().hex[:8]}"
        col.add(
            documents=[content],
            metadatas=[{
                "topic": topic,
                "session": _SESSION_ID,
                "compartment": compartment,
            }],
            ids=[entry_id],
        )
        return f"Stored to {compartment} compartment (id={entry_id}, topic='{topic}')."


class CompartmentQueryTool(BaseTool):
    name: str = "Query Compartment Memory"
    description: str = (
        "Search a specific MIRIX memory compartment or all compartments. "
        "Use 'all' as the compartment value to search across all 6 compartments. "
        "Returns the most relevant stored memories for the query."
    )
    args_schema: Type[BaseModel] = _CompQueryInput

    persist_dir: str = str(_DEFAULT_PERSIST)

    def _run(self, query: str, compartment: str = "episodic", n_results: int = 5) -> str:
        if compartment != "all" and compartment not in _COMPARTMENTS:
            return (
                f"Error: '{compartment}' is not a valid compartment. "
                f"Use one of: {', '.join(_COMPARTMENTS)} or 'all'."
            )
        targets = _COMPARTMENTS if compartment == "all" else [compartment]

        all_results: list[tuple[float, str, str, dict]] = []
        for comp in targets:
            col = _get_compartment_collection(comp, self.persist_dir)
            if col is None:
                continue
            count = col.count()
            if count == 0:
                continue
            results = col.query(
                query_texts=[query],
                n_results=min(n_results, count),
                include=["documents", "metadatas", "distances"],
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            for doc, meta, dist in zip(docs, metas, dists):
                all_results.append((1.0 - dist, comp, doc, meta))

        if not all_results:
            return "No relevant memories found."

        all_results.sort(key=lambda x: x[0], reverse=True)
        top = all_results[:n_results]
        lines = [f"Found {len(top)} relevant memory entries:\n"]
        for i, (score, comp, doc, meta) in enumerate(top, 1):
            lines.append(
                f"[{i}] compartment={comp} topic={meta.get('topic', '?')} "
                f"relevance={round(score, 3)}\n"
                f"    {doc[:300]}{'...' if len(doc) > 300 else ''}"
            )
        return "\n".join(lines)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_compartment_tools(
    config: dict,
) -> tuple[CompartmentStoreTool, CompartmentQueryTool]:
    """Return (CompartmentStoreTool, CompartmentQueryTool) configured from config dict."""
    mem_cfg = config.get("memory", {})
    if not mem_cfg.get("enabled", True):
        return CompartmentStoreTool(), CompartmentQueryTool()
    persist_dir = str(
        Path(__file__).resolve().parent.parent
        / mem_cfg.get("persist_dir", "memory/chroma")
    )
    return (
        CompartmentStoreTool(persist_dir=persist_dir),
        CompartmentQueryTool(persist_dir=persist_dir),
    )
