import pytest
import tools.file_tools as ft
from tools.file_tools import FileReadTool, FileWriteTool, FileListTool


# ── FileReadTool ───────────────────────────────────────────────────────────────

def test_read_blocks_path_traversal():
    tool = FileReadTool()
    assert FileReadTool()._run("../requirements.txt").startswith("Error: Access denied")

def test_read_returns_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    assert FileReadTool()._run("no_such_file.md").startswith("Error:")

def test_read_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    (tmp_path / "notes.md").write_text("hello", encoding="utf-8")
    assert FileReadTool()._run("notes.md") == "hello"


# ── FileWriteTool ──────────────────────────────────────────────────────────────

def test_write_blocks_path_traversal():
    assert FileWriteTool()._run("../evil.txt", "bad").startswith("Error: Access denied")

def test_write_creates_nested_subdirectory(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    FileWriteTool()._run("sub/dir/report.md", "content")
    assert (tmp_path / "sub" / "dir" / "report.md").exists()

def test_write_reports_character_count(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    result = FileWriteTool()._run("out.md", "A" * 1_234)
    assert "1,234" in result

def test_write_overwrites_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    (tmp_path / "f.md").write_text("old", encoding="utf-8")
    FileWriteTool()._run("f.md", "new")
    assert (tmp_path / "f.md").read_text(encoding="utf-8") == "new"


# ── FileListTool ───────────────────────────────────────────────────────────────

def test_list_reports_empty_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    assert "empty" in FileListTool()._run().lower()

def test_list_excludes_gitkeep(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    (tmp_path / ".gitkeep").touch()
    result = FileListTool()._run()
    assert ".gitkeep" not in result

def test_list_returns_filenames(tmp_path, monkeypatch):
    monkeypatch.setattr(ft, "_OUTPUTS_DIR", tmp_path)
    (tmp_path / "research.md").write_text("x", encoding="utf-8")
    (tmp_path / "deliverable.md").write_text("y", encoding="utf-8")
    result = FileListTool()._run()
    assert "research.md" in result
    assert "deliverable.md" in result
