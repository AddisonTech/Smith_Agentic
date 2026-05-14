"""
ui/server.py
SmithAgentic local web UI - FastAPI backend with WebSocket streaming.

Launch:
    cd smith_agentic
    python ui/server.py
    # open http://localhost:8765

Endpoints:
    GET  /                       - serves index.html
    GET  /api/status             - health check + Ollama availability
    GET  /api/models             - lists available Ollama models
    GET  /api/crew-defaults      - default model per crew
    POST /api/run                - starts a crew run; returns run_id
    GET  /api/run/{run_id}       - status and buffered output for a run
    GET  /api/outputs            - list all files in outputs/
    GET  /api/outputs/{path}     - read/download a file from outputs/
    WS   /ws/{run_id}            - streams live agent output for a run

Each crew run executes in a background thread. Agent stdout is captured
and pushed through an asyncio queue to the WebSocket client.
"""
from __future__ import annotations

import asyncio
import io
import json
import re
import sys
import threading
import uuid
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Path setup ───────────────────────────────────────────────────────────────
_UI_DIR   = Path(__file__).resolve().parent
_UNIT_DIR = _UI_DIR.parent
if str(_UNIT_DIR) not in sys.path:
    sys.path.insert(0, str(_UNIT_DIR))

from config.loader import load_config

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="SmithAgentic", version="1.0.0")

# ── Run registry ──────────────────────────────────────────────────────────────
# run_id → {"status": str, "queue": asyncio.Queue, "output": list[str], "files": list[str]}
_runs: dict[str, dict[str, Any]] = {}


# ── Request schemas ───────────────────────────────────────────────────────────
class RunRequest(BaseModel):
    goal: str
    crew: str = "default"
    model: str | None = None
    hitl: bool = False  # HITL disabled in UI mode (approval is in the UI)
    chain: bool = False  # if True, run safety then ops after the primary crew


# ── Static files (index.html) ─────────────────────────────────────────────────
@app.get("/")
async def serve_index():
    index = _UI_DIR / "index.html"
    if not index.exists():
        return JSONResponse({"error": "index.html not found"}, status_code=404)
    return FileResponse(str(index))


# ── API ───────────────────────────────────────────────────────────────────────
@app.get("/api/status")
async def api_status():
    """Health check + Ollama reachability."""
    import urllib.request
    ollama_ok = False
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = True
    except Exception:
        pass
    return {"status": "ok", "ollama": ollama_ok}


@app.get("/api/models")
async def api_models():
    """List Ollama models available locally."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.get("/api/crew-defaults")
async def api_crew_defaults():
    """Return the configured default model for each crew."""
    from config.loader import get_crew_model
    cfg = load_config()
    return {
        "default": get_crew_model(cfg, "default"),
        "plc":     get_crew_model(cfg, "plc"),
        "react":   get_crew_model(cfg, "react"),
        "vision":  get_crew_model(cfg, "vision"),
        "safety":  get_crew_model(cfg, "safety"),
        "ops":     get_crew_model(cfg, "ops"),
    }


_VALID_CREWS = {"default", "plc", "react", "vision", "safety", "ops"}


@app.post("/api/run")
async def api_run(req: RunRequest):
    """Start a crew run. Returns run_id immediately; output streams via WebSocket."""
    if req.crew not in _VALID_CREWS:
        return JSONResponse(
            {"error": f"Unknown crew '{req.crew}'. Valid: {', '.join(sorted(_VALID_CREWS))}"},
            status_code=400,
        )

    run_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()

    _runs[run_id] = {
        "status": "starting",
        "queue": queue,
        "output": [],
        "files": [],
    }

    loop = asyncio.get_running_loop()

    def _run_crew():
        from config.loader import get_crew_model
        cfg = load_config()
        # Use explicit model override if provided, else resolve per-crew default
        if req.model:
            cfg["_model_override"] = req.model
        cfg["crew"]["hitl"] = False  # UI handles approval separately

        effective_model = cfg.get("_model_override") or get_crew_model(cfg, req.crew)

        def _push(line: str):
            _runs[run_id]["output"].append(line)
            asyncio.run_coroutine_threadsafe(queue.put(line), loop)

        class _StreamCapture(io.StringIO):
            def write(self, s):
                clean = _ANSI_RE.sub('', s)
                if clean.strip():
                    _push(clean.rstrip())
                return len(s)
            def flush(self):
                pass

        _push(f"[SmithAgentic] Starting crew='{req.crew}' model='{effective_model}'")
        _push(f"[SmithAgentic] Goal: {req.goal}")
        _runs[run_id]["status"] = "running"

        try:
            # Import crew builders inside thread to avoid import-time side effects
            from crews.default_crew import build_crew as default_crew
            from crews.plc_crew import build_crew as plc_crew
            from crews.react_crew import build_crew as react_crew
            from crews.vision_crew import build_crew as vision_crew
            from crews.safety_crew import build_crew as safety_crew
            from crews.ops_crew import build_crew as ops_crew

            builders = {
                "default": default_crew, "plc": plc_crew, "react": react_crew,
                "vision": vision_crew, "safety": safety_crew, "ops": ops_crew,
            }
            builder = builders[req.crew]

            with redirect_stdout(_StreamCapture()):
                crew = builder(goal=req.goal, config=cfg)
                result = crew.kickoff()

            _push(f"\n{'='*50}")
            _push("FINAL OUTPUT")
            _push(f"{'='*50}")
            _push(str(result))

            if req.chain and req.crew not in ("safety", "ops"):
                for chain_name in ("safety", "ops"):
                    _push(f"\n[SmithAgentic] Chain: starting {chain_name} crew...")
                    with redirect_stdout(_StreamCapture()):
                        chain_crew = builders.get(chain_name)
                        if chain_crew:
                            chain_crew(goal=req.goal, config=cfg).kickoff()
                _push("[SmithAgentic] Chain complete.")

            # Collect output files (recursive so subdirs like docs/ are included)
            outputs_dir = _UNIT_DIR / "outputs"
            if outputs_dir.exists():
                _runs[run_id]["files"] = sorted(
                    str(f.relative_to(outputs_dir))
                    for f in outputs_dir.rglob("*")
                    if f.is_file() and f.name != ".gitkeep"
                )

            _runs[run_id]["status"] = "completed"
            _push("[SmithAgentic] Run completed.")

        except Exception as e:
            _runs[run_id]["status"] = "error"
            _push(f"[ERROR] {e}")
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel

    thread = threading.Thread(target=_run_crew, daemon=True)
    thread.start()

    return {"run_id": run_id}


@app.get("/api/run/{run_id}")
async def api_run_status(run_id: str):
    """Get current status and buffered output for a run."""
    if run_id not in _runs:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    run = _runs[run_id]
    return {
        "run_id": run_id,
        "status": run["status"],
        "output": run["output"],
        "files": run["files"],
    }


@app.get("/api/outputs")
async def api_list_outputs():
    """List all files in outputs/, including subdirectories."""
    outputs_dir = _UNIT_DIR / "outputs"
    if not outputs_dir.exists():
        return {"files": []}
    file_list = [
        {"path": str(f.relative_to(outputs_dir)), "size": f.stat().st_size}
        for f in outputs_dir.rglob("*")
        if f.is_file() and f.name != ".gitkeep"
    ]
    file_list.sort(key=lambda x: x["path"])
    return {"files": file_list}


@app.get("/api/outputs/{filename:path}")
async def api_get_output(filename: str):
    """Read/download a file from outputs/. Supports subdirectory paths."""
    outputs_dir = _UNIT_DIR / "outputs"
    target = (outputs_dir / filename).resolve()
    if not str(target).startswith(str(outputs_dir.resolve())):
        return JSONResponse({"error": "Access denied"}, status_code=403)
    if not target.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(str(target), filename=Path(filename).name)


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws/{run_id}")
async def websocket_stream(websocket: WebSocket, run_id: str):
    """Stream live output lines for a run."""
    await websocket.accept()

    if run_id not in _runs:
        await websocket.send_text(json.dumps({"type": "error", "msg": "Run not found"}))
        await websocket.close()
        return

    queue = _runs[run_id]["queue"]

    # Flush any buffered output first
    for line in _runs[run_id]["output"]:
        await websocket.send_text(json.dumps({"type": "output", "line": line}))

    try:
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
                continue

            if line is None:  # sentinel - run finished
                run = _runs[run_id]
                await websocket.send_text(json.dumps({
                    "type": "done",
                    "status": run["status"],
                    "files": run["files"],
                }))
                break

            await websocket.send_text(json.dumps({"type": "output", "line": line}))

    except WebSocketDisconnect:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  SmithAgentic Web UI")
    print("=" * 50)
    print("  URL:  http://localhost:8765")
    print("  API:  http://localhost:8765/api/status")
    print("  Stop: Ctrl+C")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")
