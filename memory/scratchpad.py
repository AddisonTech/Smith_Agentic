"""
memory/scratchpad.py
Shared blackboard / scratchpad — all agents in a crew can read and write.

Implements the LbMAS (Layered blackboard Multi-Agent System) pattern. Each agent
appends its section to a shared JSON file. Other agents read the full scratchpad
before acting, giving every agent visibility into what upstream agents have done.

Storage: outputs/checkpoints/scratchpad_{run_id}.json

Usage:
    from memory.scratchpad import get_scratchpad

    pad = get_scratchpad(run_id)
    pad.write("Orchestrator", "plan", "Step 1: Research, Step 2: Build ...")
    pad.write("Researcher", "findings", "Found 3 relevant papers ...")

    context = pad.read_all_as_text()   # pass to agents as additional context
    plan    = pad.read("Orchestrator") # {"plan": "..."}
    pad.clear()                        # reset for next run
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_SCRATCH_DIR = Path(__file__).resolve().parent.parent / "outputs" / "checkpoints"

_scratchpads: dict[str, "Scratchpad"] = {}


class Scratchpad:
    def __init__(self, run_id: str):
        _SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self._path = _SCRATCH_DIR / f"scratchpad_{run_id}.json"
        self._lock = threading.Lock()
        if not self._path.exists():
            self._path.write_text(json.dumps({}, indent=2), encoding="utf-8")

    def write(self, agent_name: str, section: str, content: str) -> None:
        """Write or overwrite agent_name/section with content."""
        with self._lock:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if agent_name not in data:
                data[agent_name] = {}
            data[agent_name][section] = content
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read(self, agent_name: str | None = None) -> dict:
        """Return the full scratchpad dict, or a single agent's sections."""
        with self._lock:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data.get(agent_name, {}) if agent_name else data

    def read_all_as_text(self) -> str:
        """Return the full scratchpad as a human-readable string for agent context."""
        data = self.read()
        if not data:
            return "=== SHARED SCRATCHPAD (empty) ==="
        lines = ["=== SHARED SCRATCHPAD ==="]
        for agent, sections in data.items():
            lines.append(f"\n[{agent}]")
            for section, content in sections.items():
                preview = content[:500] if isinstance(content, str) else str(content)[:500]
                ellipsis = "..." if isinstance(content, str) and len(content) > 500 else ""
                lines.append(f"  {section}: {preview}{ellipsis}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset the scratchpad to empty."""
        with self._lock:
            self._path.write_text(json.dumps({}, indent=2), encoding="utf-8")


def get_scratchpad(run_id: str) -> Scratchpad:
    """Return the Scratchpad for run_id, creating it if needed."""
    if run_id not in _scratchpads:
        _scratchpads[run_id] = Scratchpad(run_id)
    return _scratchpads[run_id]
