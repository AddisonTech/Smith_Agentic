"""
tests/test_mcp_tools.py
Tests for the MCP-client integration that wires the OT bridges into crews.

The write-gating tests are pure unit tests (no network). The Hermes integration
test launches the real Hermes MCP server over stdio and confirms its READ tools
are discovered and adapted into CrewAI tools — it does NOT require a live OPC-UA
server, because Hermes connects to OPC-UA lazily (only on actual tool calls),
so tool *discovery* succeeds regardless.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.mcp_tools import _writes_allowed, _allowed_tool_names, build_mcp_tools, stop_mcp_servers

_HERMES_DIR = Path(__file__).resolve().parent.parent.parent / "Hermes"

_HERMES_CFG = {
    "enabled": True,
    "transport": "stdio",
    "args": ["-m", "hermes_mcp.server"],
    "cwd": "../Hermes",
    "env": {"HERMES_ENDPOINT": "opc.tcp://localhost:4840"},
    "connect_timeout": 15,
    "crews": ["plc"],
    "read_tools": ["read_node", "read_nodes", "browse_nodes", "get_server_status", "get_node_attributes"],
    "write_tools": ["write_node"],
    "allow_writes": False,
    "write_token": "",
}


# ── Write gating (#4) ─────────────────────────────────────────────────────────

def test_writes_blocked_by_default(monkeypatch):
    monkeypatch.delenv("SMITH_AGENTIC_MCP_ALLOW_WRITES", raising=False)
    assert _writes_allowed({"allow_writes": True}) is False
    assert _writes_allowed({"allow_writes": False}) is False


def test_writes_need_both_config_and_env(monkeypatch):
    monkeypatch.setenv("SMITH_AGENTIC_MCP_ALLOW_WRITES", "true")
    assert _writes_allowed({"allow_writes": True}) is True
    # env on but config off -> still blocked
    assert _writes_allowed({"allow_writes": False}) is False


def test_writes_require_matching_token(monkeypatch):
    monkeypatch.setenv("SMITH_AGENTIC_MCP_ALLOW_WRITES", "true")
    cfg = {"allow_writes": True, "write_token": "s3cret"}
    monkeypatch.delenv("SMITH_AGENTIC_MCP_WRITE_TOKEN", raising=False)
    assert _writes_allowed(cfg) is False
    monkeypatch.setenv("SMITH_AGENTIC_MCP_WRITE_TOKEN", "wrong")
    assert _writes_allowed(cfg) is False
    monkeypatch.setenv("SMITH_AGENTIC_MCP_WRITE_TOKEN", "s3cret")
    assert _writes_allowed(cfg) is True


def test_allowed_tool_names_excludes_writes_by_default(monkeypatch):
    monkeypatch.delenv("SMITH_AGENTIC_MCP_ALLOW_WRITES", raising=False)
    names = _allowed_tool_names(_HERMES_CFG)
    assert "read_node" in names
    assert "write_node" not in names


def test_allowed_tool_names_includes_writes_when_unlocked(monkeypatch):
    monkeypatch.setenv("SMITH_AGENTIC_MCP_ALLOW_WRITES", "true")
    cfg = dict(_HERMES_CFG, allow_writes=True)
    names = _allowed_tool_names(cfg)
    assert "write_node" in names


# ── Hermes integration (real stdio server, no OPC-UA needed) ──────────────────

@pytest.mark.skipif(not _HERMES_DIR.exists(), reason="Hermes repo not present alongside Smith_Agentic")
def test_hermes_read_tools_discovered(monkeypatch):
    monkeypatch.delenv("SMITH_AGENTIC_MCP_ALLOW_WRITES", raising=False)
    config = {"mcp_servers": {"hermes": _HERMES_CFG}}
    try:
        tools = build_mcp_tools(config, "plc")
        names = {t.name for t in tools}
        assert "read_node" in names, f"expected read tools, got {names}"
        assert "get_server_status" in names
        # write_node must NOT be exposed while writes are gated.
        assert "write_node" not in names
    finally:
        stop_mcp_servers()


@pytest.mark.skipif(not _HERMES_DIR.exists(), reason="Hermes repo not present alongside Smith_Agentic")
def test_disabled_server_yields_no_tools():
    config = {"mcp_servers": {"hermes": dict(_HERMES_CFG, enabled=False)}}
    assert build_mcp_tools(config, "plc") == []


def test_no_servers_configured():
    assert build_mcp_tools({}, "plc") == []
