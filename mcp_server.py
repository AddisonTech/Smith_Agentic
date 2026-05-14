"""
mcp_server.py
SmithAgentic MCP server - exposes crew runs as tools for Claude Desktop
and Claude Code via the Model Context Protocol (stdio transport).

Setup - Claude Code:
    claude mcp add smith_agentic python C:/path/to/Smith_Agentic/mcp_server.py

Setup - Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "smith_agentic": {
          "command": "python",
          "args": ["C:/path/to/Smith_Agentic/mcp_server.py"]
        }
      }
    }

Tools exposed:
    check_ollama        - verify Ollama is running
    list_crews          - show available crews and descriptions
    list_models         - show installed Ollama models
    run_crew            - start a crew run, returns run_id
    get_run_status      - poll a run for progress and output
    list_output_files   - list files in outputs/
    read_output_file    - read a specific file from outputs/
"""
from __future__ import annotations

import sys
import threading
import uuid
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SmithAgentic")

# ── Run registry ──────────────────────────────────────────────────────────────
_runs: dict[str, dict[str, Any]] = {}

_CREWS: dict[str, str] = {
    "default": "General crew: plan, research, build, critique.",
    "plc":     "Rockwell/Allen-Bradley Logix PLC development.",
    "react":   "Industrial React/MUI HMI development.",
    "vision":  "Vision_Inspect defect analysis (requires Vision_Inspect on port 8000).",
    "safety":  "QA, security, and deployment validation. Runs against existing outputs/.",
    "ops":     "Documentation, memory consolidation, and telemetry. Runs against existing outputs/.",
}


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def check_ollama() -> str:
    """Check whether Ollama is running and reachable on localhost:11434."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return "Ollama is running at http://localhost:11434."
    except Exception:
        return (
            "Cannot reach Ollama at http://localhost:11434. "
            "Run `ollama serve` in a terminal and try again."
        )


@mcp.tool()
def list_crews() -> str:
    """List all available SmithAgentic crews and what they do."""
    lines = ["Available crews:\n"]
    for name, desc in _CREWS.items():
        lines.append(f"  {name:<10} {desc}")
    lines.append("\nPass a crew name to run_crew() to start a run.")
    return "\n".join(lines)


@mcp.tool()
def list_models() -> str:
    """List Ollama models currently installed on this machine."""
    import json, urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
    except Exception:
        return "Cannot reach Ollama. Run `ollama serve` first."
    if not models:
        return "Ollama is running but no models are installed. Run `ollama pull qwen2.5:7b`."
    return "Installed Ollama models:\n" + "\n".join(f"  {m}" for m in models)


@mcp.tool()
def run_crew(
    goal: str,
    crew: str = "default",
    model: str | None = None,
    chain: bool = False,
) -> str:
    """
    Start a SmithAgentic crew run in the background.

    Args:
        goal:  What you want the crew to accomplish.
        crew:  Which crew to run. Call list_crews() to see options. Default: 'default'.
        model: Ollama model override for this run (e.g. 'qwen2.5:14b').
               Omit to use the crew's configured default from config.yaml.
        chain: Set True to automatically run the safety crew then ops crew
               after the primary crew completes.

    Returns a run_id string. Call get_run_status(run_id) to poll for progress
    and results. Crew runs take several minutes - poll every 30-60 seconds.
    """
    if crew not in _CREWS:
        return (
            f"Unknown crew '{crew}'. "
            f"Valid options: {', '.join(_CREWS)}. "
            "Call list_crews() for descriptions."
        )

    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {"status": "starting", "output": [], "files": []}

    def _worker():
        from config.loader import load_config, get_crew_model
        from crews.default_crew import build_crew as _default
        from crews.plc_crew    import build_crew as _plc
        from crews.react_crew  import build_crew as _react
        from crews.vision_crew import build_crew as _vision
        from crews.safety_crew import build_crew as _safety
        from crews.ops_crew    import build_crew as _ops

        builders = {
            "default": _default,
            "plc":     _plc,
            "react":   _react,
            "vision":  _vision,
            "safety":  _safety,
            "ops":     _ops,
        }

        def _log(msg: str):
            _runs[run_id]["output"].append(msg)

        try:
            cfg = load_config()
            cfg["crew"]["hitl"] = False   # MCP runs are non-interactive
            if model:
                cfg["_model_override"] = model

            effective = cfg.get("_model_override") or get_crew_model(cfg, crew)
            _log(f"[SmithAgentic] crew={crew}  model={effective}  chain={chain}")
            _log(f"[SmithAgentic] goal: {goal}")
            _runs[run_id]["status"] = "running"

            builders[crew](goal=goal, config=cfg).kickoff()

            if chain and crew not in ("safety", "ops"):
                for name in ("safety", "ops"):
                    _log(f"[SmithAgentic] chain: starting {name} crew...")
                    builders[name](goal=goal, config=cfg).kickoff()

            outputs_dir = _HERE / "outputs"
            if outputs_dir.exists():
                _runs[run_id]["files"] = sorted(
                    f.name for f in outputs_dir.iterdir()
                    if f.is_file() and f.name != ".gitkeep"
                )

            _runs[run_id]["status"] = "completed"
            _log("[SmithAgentic] Run completed.")

        except Exception as exc:
            _runs[run_id]["status"] = "error"
            _log(f"[ERROR] {exc}")

    threading.Thread(target=_worker, daemon=True).start()
    return (
        f"Run started.\n"
        f"  run_id : {run_id}\n"
        f"  crew   : {crew}\n"
        f"  chain  : {chain}\n"
        f"  goal   : {goal}\n\n"
        f"Call get_run_status('{run_id}') to check progress. "
        f"Crew runs take several minutes - poll every 30-60 seconds."
    )


@mcp.tool()
def get_run_status(run_id: str) -> str:
    """
    Get the current status and recent output of a crew run.

    Args:
        run_id: The ID returned by run_crew().

    Status values:
        starting   - crew is being initialized
        running    - agents are actively working
        completed  - run finished successfully
        error      - run failed (check output for details)

    When status is 'completed', call list_output_files() and read_output_file()
    to access the results.
    """
    run = _runs.get(run_id)
    if not run:
        known = list(_runs.keys())
        suffix = f"Active run IDs: {known}" if known else "No runs started in this session."
        return f"Run ID '{run_id}' not found. {suffix}"

    status  = run["status"]
    all_out = run["output"]
    recent  = all_out[-20:]
    files   = run.get("files", [])

    lines = [
        f"status : {status}",
        f"lines  : {len(all_out)} total (showing last {len(recent)})",
        "",
    ]
    lines.extend(recent)
    if files:
        lines.append(f"\noutput files: {', '.join(files)}")
    if status == "completed":
        lines.append("\nRun is done. Use list_output_files() and read_output_file() to read results.")
    elif status == "running":
        lines.append("\nStill running. Poll again in 30-60 seconds.")
    return "\n".join(lines)


@mcp.tool()
def list_output_files() -> str:
    """List all files currently in the outputs/ directory."""
    outputs_dir = _HERE / "outputs"
    if not outputs_dir.exists():
        return "outputs/ directory does not exist."
    files = sorted(
        f for f in outputs_dir.iterdir()
        if f.is_file() and f.name != ".gitkeep"
    )
    if not files:
        return "outputs/ is empty. Run a crew first."
    lines = [f"Files in outputs/ ({len(files)} total):"]
    for f in files:
        kb = f.stat().st_size / 1024
        lines.append(f"  {f.name:<40} {kb:.1f} KB")
    lines.append("\nUse read_output_file(filename) to read any of these.")
    return "\n".join(lines)


@mcp.tool()
def read_output_file(filename: str) -> str:
    """
    Read a file from the outputs/ directory.

    Args:
        filename: File name to read (e.g. 'deliverable.md', 'qa_report.md').
                  Call list_output_files() to see what is available.
    """
    outputs_dir = _HERE / "outputs"
    target = (outputs_dir / filename).resolve()
    if not str(target).startswith(str(outputs_dir.resolve())):
        return "Access denied."
    if not target.exists():
        return f"'{filename}' not found. Call list_output_files() to see what is available."
    content = target.read_text(encoding="utf-8", errors="replace")
    if len(content) > 20_000:
        content = content[:20_000] + f"\n\n... (truncated at 20,000 chars)"
    return f"--- {filename} ---\n{content}"


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
