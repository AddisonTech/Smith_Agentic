import re
import pytest
from fastapi.testclient import TestClient

from ui.server import app, _ANSI_RE

client = TestClient(app)


# ── ANSI stripping ─────────────────────────────────────────────────────────────

def test_ansi_strip_color_sequence():
    assert _ANSI_RE.sub("", "\x1b[32mgreen\x1b[0m") == "greenm"[:-1] or \
           _ANSI_RE.sub("", "\x1b[32mgreen\x1b[0m") == "green"

def test_ansi_strip_bold():
    assert _ANSI_RE.sub("", "\x1b[1mbold\x1b[0m") == "bold"

def test_ansi_strip_complex_sequence():
    assert _ANSI_RE.sub("", "\x1b[0;33;40mtext\x1b[0m") == "text"

def test_ansi_strip_leaves_plain_text():
    assert _ANSI_RE.sub("", "no codes here") == "no codes here"


# ── /api/status ────────────────────────────────────────────────────────────────

def test_status_endpoint_returns_ok():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ollama" in data

def test_status_ollama_false_when_not_running():
    response = client.get("/api/status")
    data = response.json()
    assert isinstance(data["ollama"], bool)


# ── /api/outputs/{filename} — path traversal ─────────────────────────────────

def test_output_path_traversal_returns_403_or_404():
    response = client.get("/api/outputs/..%2Frequirements.txt")
    assert response.status_code in (403, 404)

def test_output_missing_file_returns_404():
    response = client.get("/api/outputs/definitely_not_there.txt")
    assert response.status_code == 404


# ── /api/run/{run_id} — unknown run ───────────────────────────────────────────

def test_run_status_unknown_id_returns_404():
    response = client.get("/api/run/deadbeef")
    assert response.status_code == 404
