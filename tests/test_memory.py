import pytest
from unittest.mock import patch

import memory.memory_store as ms
from memory.memory_store import MemoryStoreTool, MemoryQueryTool, create_memory_tools


# ── create_memory_tools factory ───────────────────────────────────────────────

def test_factory_returns_tool_instances():
    store, query = create_memory_tools({"memory": {"enabled": False}})
    assert isinstance(store, MemoryStoreTool)
    assert isinstance(query, MemoryQueryTool)

def test_factory_uses_configured_collection():
    cfg = {"memory": {"enabled": True, "collection": "my_col", "persist_dir": "memory/chroma"}}
    store, query = create_memory_tools(cfg)
    assert store.collection_name == "my_col"
    assert query.collection_name == "my_col"

def test_factory_defaults_to_standard_collection():
    store, _ = create_memory_tools({"memory": {"enabled": True}})
    assert store.collection_name == "smith_agentic_memory"

def test_factory_enabled_false_returns_default_tools():
    store, query = create_memory_tools({"memory": {"enabled": False}})
    assert store.collection_name == "smith_agentic_memory"


# ── MemoryStoreTool — graceful fallback when ChromaDB unavailable ─────────────

def test_store_tool_reports_disabled_when_collection_unavailable():
    store = MemoryStoreTool()
    with patch.object(ms, "_get_collection", return_value=None):
        result = store._run("some content", "test topic")
    assert "disabled" in result.lower() or "chromadb" in result.lower()


# ── MemoryQueryTool — graceful fallback when ChromaDB unavailable ─────────────

def test_query_tool_reports_disabled_when_collection_unavailable():
    query = MemoryQueryTool()
    with patch.object(ms, "_get_collection", return_value=None):
        result = query._run("some query", 5)
    assert "disabled" in result.lower() or "chromadb" in result.lower()

def test_query_tool_reports_empty_when_collection_has_no_entries():
    query = MemoryQueryTool()
    mock_col = type("Col", (), {"count": lambda self: 0})()
    with patch.object(ms, "_get_collection", return_value=mock_col):
        result = query._run("anything", 5)
    assert "empty" in result.lower()
