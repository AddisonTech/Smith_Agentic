"""
tools/mcp_tools.py
Connect Smith_Agentic crews to external MCP tool servers (the OT bridges).

Smith_Agentic acts as an MCP *client* here: it launches/connects to MCP servers
- Hermes        (OPC-UA plant-floor data, stdio transport)
- ignition-mcp  (Ignition SCADA gateway, streamable-http transport)
and exposes their tools to CrewAI agents.

Two safety properties are baked in:

  * Read tools are exposed by default; WRITE / mutating tools are gated behind an
    explicit, multi-factor opt-in (see ``_writes_allowed``). This mirrors
    ignition-mcp's own "script execution disabled by default" pattern so that an
    agent can never write to the plant floor by accident.

  * Server failures are non-fatal. If a bridge is unreachable (OPC-UA down, gateway
    offline, deps missing) we log a warning and return no tools for it — the crew
    still runs, just without that bridge's tools.

Lifecycle: an ``MCPServerAdapter`` must stay connected for the whole duration of a
crew's ``kickoff()``. Started adapters are held in a module-level registry and
stopped at interpreter exit. Call ``stop_mcp_servers()`` to close them sooner
(e.g. a long-lived server process after each run).
"""
from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("smith_agentic.mcp")

# Smith_Agentic/ — used to resolve relative `cwd` entries in config.
_SMITH_ROOT = Path(__file__).resolve().parent.parent

# Adapters that have been started, kept alive for the process lifetime.
_ACTIVE_ADAPTERS: list[Any] = []
_CLEANUP_REGISTERED = False

_TRUTHY = {"1", "true", "yes", "on"}


# ── Write gating (#4: plant-floor writes are opt-in) ──────────────────────────

def _writes_allowed(server_cfg: dict) -> bool:
    """
    Expose a server's WRITE / mutating tools to agents only when ALL hold:

      1. The server config sets ``allow_writes: true``.
      2. The env flag ``SMITH_AGENTIC_MCP_ALLOW_WRITES`` is truthy.
      3. If the server config sets ``write_token``, the env var
         ``SMITH_AGENTIC_MCP_WRITE_TOKEN`` must match it.

    Reads are always allowed. Writes require a deliberate, auditable choice.
    """
    if not server_cfg.get("allow_writes", False):
        return False
    if os.environ.get("SMITH_AGENTIC_MCP_ALLOW_WRITES", "").strip().lower() not in _TRUTHY:
        return False
    required = server_cfg.get("write_token")
    if required:
        return os.environ.get("SMITH_AGENTIC_MCP_WRITE_TOKEN", "") == str(required)
    return True


def _allowed_tool_names(server_cfg: dict) -> list[str]:
    """Read tools, plus write tools only when writes are unlocked."""
    names = list(server_cfg.get("read_tools", []) or [])
    if _writes_allowed(server_cfg):
        names += list(server_cfg.get("write_tools", []) or [])
    return names


# ── Server params ─────────────────────────────────────────────────────────────

def _resolve_cwd(cwd: str | None) -> str | None:
    if not cwd:
        return None
    p = Path(cwd).expanduser()
    if not p.is_absolute():
        p = (_SMITH_ROOT / cwd).resolve()
    return str(p)


def _build_server_params(cfg: dict):
    """Return a serverparams object/dict for MCPServerAdapter, or None if invalid."""
    transport = (cfg.get("transport") or "stdio").lower()

    if transport == "stdio":
        from mcp import StdioServerParameters

        # Spawn the bridge with the SAME interpreter running Smith_Agentic so it
        # shares the installed deps, unless the config overrides `command`.
        command = cfg.get("command") or sys.executable
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
        return StdioServerParameters(
            command=command,
            args=list(cfg.get("args", []) or []),
            env=env,
            cwd=_resolve_cwd(cfg.get("cwd")),
        )

    if transport in ("streamable-http", "http", "sse"):
        url = cfg.get("url")
        if not url:
            logger.warning("MCP server has http transport but no 'url'; skipping.")
            return None
        return {"url": url, "transport": "sse" if transport == "sse" else "streamable-http"}

    logger.warning("Unknown MCP transport '%s'; skipping.", transport)
    return None


# ── Public API ──────────────────────────────────────────────────────────────

def build_mcp_tools(config: dict, crew_name: str) -> list:
    """
    Start every enabled MCP server whose ``crews`` list includes ``crew_name`` and
    return the combined list of CrewAI tools (filtered to the allowed tool names).

    Never raises on a server failure: a bad/unavailable server is logged and
    contributes zero tools.
    """
    servers = (config or {}).get("mcp_servers") or {}
    if not servers:
        return []

    try:
        from crewai_tools import MCPServerAdapter
        # crewai-tools defines the class even when its MCP deps (mcp + mcpadapt)
        # are missing, but constructing it then PROMPTS on stdin to install them.
        # Guard against that so a missing dep degrades gracefully instead of hanging.
        from crewai_tools.adapters.mcp_adapter import MCP_AVAILABLE
        if not MCP_AVAILABLE:
            raise ImportError("crewai-tools MCP extras not installed (need 'mcp' and 'mcpadapt')")
    except Exception as exc:  # crewai-tools / mcp / mcpadapt not installed
        logger.warning("crewai-tools MCP support unavailable (%s); no MCP tools loaded.", exc)
        return []

    collected: list = []
    for name, cfg in servers.items():
        cfg = cfg or {}
        if not cfg.get("enabled", False):
            continue
        crews = cfg.get("crews")
        if crews and crew_name not in crews:
            continue

        allowed = _allowed_tool_names(cfg)
        if not allowed:
            logger.info("MCP server '%s' enabled but exposes no tools (writes gated?).", name)
            continue

        params = _build_server_params(cfg)
        if params is None:
            continue

        timeout = int(cfg.get("connect_timeout", 8))
        try:
            # MCPServerAdapter.__init__ starts the server itself (and self-cleans
            # on failure), so we must NOT call start() again.
            adapter = MCPServerAdapter(params, *allowed, connect_timeout=timeout)
        except Exception as exc:
            logger.warning(
                "MCP server '%s' failed to start (%s); crew '%s' will run without it.",
                name, exc, crew_name,
            )
            continue

        tools = list(adapter.tools or [])
        _register(adapter)
        collected.extend(tools)
        writes = " +writes" if _writes_allowed(cfg) else " (read-only)"
        logger.info("MCP server '%s' connected: %d tools%s.", name, len(tools), writes)

    return collected


def _register(adapter: Any) -> None:
    global _CLEANUP_REGISTERED
    _ACTIVE_ADAPTERS.append(adapter)
    if not _CLEANUP_REGISTERED:
        atexit.register(stop_mcp_servers)
        _CLEANUP_REGISTERED = True


def stop_mcp_servers() -> None:
    """Stop all started MCP adapters. Safe to call multiple times."""
    while _ACTIVE_ADAPTERS:
        adapter = _ACTIVE_ADAPTERS.pop()
        try:
            adapter.stop()
        except Exception as exc:
            logger.debug("Error stopping MCP adapter: %s", exc)
