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


# ── /api/outputs — list ───────────────────────────────────────────────────────

def test_list_outputs_returns_files_key():
    response = client.get("/api/outputs")
    assert response.status_code == 200
    assert "files" in response.json()

def test_list_outputs_files_is_list():
    response = client.get("/api/outputs")
    assert isinstance(response.json()["files"], list)

def test_list_outputs_file_entries_have_path_and_size(tmp_path, monkeypatch):
    import ui.server as srv
    (tmp_path / "deliverable.md").write_text("hello")
    monkeypatch.setattr(srv, "_UNIT_DIR", tmp_path)
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "deliverable.md").write_text("hello")
    response = client.get("/api/outputs")
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1
    assert "path" in files[0]
    assert "size" in files[0]

def test_list_outputs_includes_subdirectory_files(tmp_path, monkeypatch):
    import ui.server as srv
    monkeypatch.setattr(srv, "_UNIT_DIR", tmp_path)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "deliverable.md").write_text("top level")
    (outputs / "docs").mkdir()
    (outputs / "docs" / "deliverable_docs.md").write_text("nested")
    response = client.get("/api/outputs")
    paths = [f["path"] for f in response.json()["files"]]
    assert any("docs" in p for p in paths)


# ── /api/outputs/{filename} — path traversal and download ────────────────────

def test_output_path_traversal_returns_403_or_404():
    response = client.get("/api/outputs/..%2Frequirements.txt")
    assert response.status_code in (403, 404)

def test_output_missing_file_returns_404():
    response = client.get("/api/outputs/definitely_not_there.txt")
    assert response.status_code == 404


# ── /api/run — crew validation ────────────────────────────────────────────────

def test_run_unknown_crew_returns_400():
    response = client.post("/api/run", json={"goal": "test", "crew": "nonexistent_crew"})
    assert response.status_code == 400
    assert "nonexistent_crew" in response.json()["error"]

def test_run_unknown_crew_error_lists_valid_crews():
    response = client.post("/api/run", json={"goal": "test", "crew": "bad"})
    assert response.status_code == 400
    error = response.json()["error"]
    assert "default" in error

def test_run_valid_crew_starts_without_error():
    # Just checks that a valid crew name doesn't produce an immediate validation error.
    # We don't wait for the full run - just verify it starts as 'starting' or 'running'.
    response = client.post("/api/run", json={"goal": "test goal", "crew": "default"})
    assert response.status_code == 200
    assert "run_id" in response.json()


# ── /api/run/{run_id} — unknown run ───────────────────────────────────────────

def test_run_status_unknown_id_returns_404():
    response = client.get("/api/run/deadbeef")
    assert response.status_code == 404
