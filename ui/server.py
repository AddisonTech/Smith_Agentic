"""
ui/server.py
SmithAgentic local web UI - FastAPI backend with WebSocket streaming.

Launch:
    cd smith_agentic
    python ui/server.py
    # open http://localhost:8765

Endpoints:
    GET  /                          - serves index.html
    GET  /api/status                - health check + Ollama availability
    GET  /api/models                - lists available Ollama models
    GET  /api/crew-defaults         - default model per crew
    POST /api/run                   - starts a crew run; returns run_id
    GET  /api/run/{run_id}          - status and buffered output for a run
    POST /api/run/{run_id}/cancel   - cancel an active run
    GET  /api/outputs               - list all files in outputs/
    GET  /api/outputs/{path}        - read/download a file from outputs/
    WS   /ws/{run_id}               - streams live agent output for a run

Environment variables:
    SMITH_AGENTIC_OLLAMA_URL   Ollama base URL (default: http://localhost:11434)
    SMITH_AGENTIC_CORS_ORIGINS Comma-separated allowed origins (default: localhost dev + GitHub Pages)

Each crew run executes in a background thread. Agent stdout is captured
and pushed through an asyncio queue to the WebSocket client.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sqlite3
import sys
import threading
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
_UI_DIR   = Path(__file__).resolve().parent
_UNIT_DIR = _UI_DIR.parent
if str(_UNIT_DIR) not in sys.path:
    sys.path.insert(0, str(_UNIT_DIR))

from config.loader import load_config

# ── Env config ────────────────────────────────────────────────────────────────
_OLLAMA_URL = os.environ.get("SMITH_AGENTIC_OLLAMA_URL", "http://localhost:11434").rstrip("/")

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:3000",
    "https://addisontech.github.io",
]
_cors_env = os.environ.get("SMITH_AGENTIC_CORS_ORIGINS", "")
_CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] or _DEFAULT_ORIGINS

# ── SQLite persistence ────────────────────────────────────────────────────────
_DB_PATH = _UNIT_DIR / "runs.db"
_db_lock = threading.Lock()


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db_init():
    with _db_lock:
        conn = _db_connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id     TEXT PRIMARY KEY,
                crew       TEXT NOT NULL,
                goal       TEXT NOT NULL,
                status     TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()


def _db_upsert(run_id: str, crew: str, goal: str, status: str):
    now = datetime.now(timezone.utc).isoformat()
    with _db_lock:
        conn = _db_connect()
        conn.execute("""
            INSERT INTO runs (run_id, crew, goal, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status     = excluded.status,
                updated_at = excluded.updated_at
        """, (run_id, crew, goal, status, now, now))
        conn.commit()
        conn.close()


def _db_load_all() -> list[sqlite3.Row]:
    with _db_lock:
        conn = _db_connect()
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        conn.close()
    return rows


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="SmithAgentic", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Run registry ──────────────────────────────────────────────────────────────
# run_id → {status, queue, output, files, stop_event, crew, goal}
_runs: dict[str, dict[str, Any]] = {}


def _set_status(run_id: str, status: str):
    """Update run status in memory and persist to SQLite."""
    run = _runs.get(run_id)
    if run:
        run["status"] = status
        _db_upsert(run_id, run["crew"], run["goal"], status)


# ── Startup: load persisted runs ──────────────────────────────────────────────
@app.on_event("startup")
async def _startup():
    _db_init()
    loop = asyncio.get_running_loop()
    for row in _db_load_all():
        rid = row["run_id"]
        # Mark anything that was mid-run as error (server was killed)
        status = row["status"]
        if status in ("starting", "running"):
            status = "error"
            _db_upsert(rid, row["crew"], row["goal"], status)
        _runs[rid] = {
            "status":     status,
            "queue":      asyncio.Queue(),
            "output":     [f"[SmithAgentic] Restored from previous session. Final status: {status}"],
            "files":      [],
            "stop_event": threading.Event(),
            "crew":       row["crew"],
            "goal":       row["goal"],
        }


# ── Request schemas ───────────────────────────────────────────────────────────
class RunRequest(BaseModel):
    goal: str
    crew: str = "default"
    model: str | None = None
    hitl: bool = False
    chain: bool = False


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
        urllib.request.urlopen(f"{_OLLAMA_URL}/api/tags", timeout=2)
        ollama_ok = True
    except Exception:
        pass
    return {"status": "ok", "ollama": ollama_ok}


@app.get("/api/models")
async def api_models():
    """List Ollama models available locally."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{_OLLAMA_URL}/api/tags", timeout=5) as r:
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
    stop_event = threading.Event()

    _runs[run_id] = {
        "status":     "starting",
        "queue":      queue,
        "output":     [],
        "files":      [],
        "stop_event": stop_event,
        "crew":       req.crew,
        "goal":       req.goal,
    }
    _db_upsert(run_id, req.crew, req.goal, "starting")

    loop = asyncio.get_running_loop()

    def _run_crew():
        from config.loader import get_crew_model
        cfg = load_config()
        if req.model:
            cfg["_model_override"] = req.model
        cfg["crew"]["hitl"] = False

        effective_model = cfg.get("_model_override") or get_crew_model(cfg, req.crew)

        def _push(line: str):
            if stop_event.is_set():
                return
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

        if stop_event.is_set():
            _set_status(run_id, "cancelled")
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            return

        _push(f"[SmithAgentic] Starting crew='{req.crew}' model='{effective_model}'")
        _push(f"[SmithAgentic] Goal: {req.goal}")
        _set_status(run_id, "running")

        try:
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

            if stop_event.is_set():
                _set_status(run_id, "cancelled")
                _push("[SmithAgentic] Run cancelled before kickoff.")
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
                return

            with redirect_stdout(_StreamCapture()):
                crew = builder(goal=req.goal, config=cfg)
                result = crew.kickoff()

            if stop_event.is_set():
                _set_status(run_id, "cancelled")
                _push("[SmithAgentic] Run cancelled after kickoff.")
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
                return

            _push(f"\n{'='*50}")
            _push("FINAL OUTPUT")
            _push(f"{'='*50}")
            _push(str(result))

            if req.chain and req.crew not in ("safety", "ops"):
                for chain_name in ("safety", "ops"):
                    if stop_event.is_set():
                        break
                    _push(f"\n[SmithAgentic] Chain: starting {chain_name} crew...")
                    with redirect_stdout(_StreamCapture()):
                        chain_crew = builders.get(chain_name)
                        if chain_crew:
                            chain_crew(goal=req.goal, config=cfg).kickoff()
                _push("[SmithAgentic] Chain complete.")

            outputs_dir = _UNIT_DIR / "outputs"
            if outputs_dir.exists():
                _runs[run_id]["files"] = sorted(
                    str(f.relative_to(outputs_dir))
                    for f in outputs_dir.rglob("*")
                    if f.is_file() and f.name != ".gitkeep"
                )

            if stop_event.is_set():
                _set_status(run_id, "cancelled")
                _push("[SmithAgentic] Run cancelled.")
            else:
                _set_status(run_id, "completed")
                _push("[SmithAgentic] Run completed.")

        except Exception as e:
            _set_status(run_id, "error")
            _push(f"[ERROR] {e}")
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    thread = threading.Thread(target=_run_crew, daemon=True)
    thread.start()

    return {"run_id": run_id}


@app.post("/api/run/{run_id}/cancel")
async def api_cancel_run(run_id: str):
    """Signal a running crew to stop. Sets status to 'cancelled'."""
    if run_id not in _runs:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    run = _runs[run_id]
    if run["status"] not in ("starting", "running"):
        return JSONResponse(
            {"error": f"Run is not active (status: {run['status']})"},
            status_code=400,
        )
    run["stop_event"].set()
    return {"run_id": run_id, "status": "cancelling"}


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
        "files":  run["files"],
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

    # If run already finished, send done immediately
    if _runs[run_id]["status"] not in ("starting", "running"):
        run = _runs[run_id]
        await websocket.send_text(json.dumps({
            "type":   "done",
            "status": run["status"],
            "files":  run["files"],
        }))
        await websocket.close()
        return

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
                    "type":   "done",
                    "status": run["status"],
                    "files":  run["files"],
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
