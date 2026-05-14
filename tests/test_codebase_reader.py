import pytest
import tools.codebase_reader as cr
from tools.codebase_reader import CodebaseReadTool, CodebaseListTool, CodebaseGlobTool, _MAX_FILE_CHARS


# ── CodebaseReadTool ───────────────────────────────────────────────────────────

def test_read_blocks_path_traversal():
    assert "Access denied" in CodebaseReadTool()._run("../../etc/passwd")

def test_read_returns_error_for_missing_file():
    assert "not found" in CodebaseReadTool()._run("definitely_not_a_real_file_xyz.py")

def test_read_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    (tmp_path / "hello.py").write_text("print('hi')", encoding="utf-8")
    result = CodebaseReadTool()._run("hello.py")
    assert "print('hi')" in result

def test_read_truncates_large_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    (tmp_path / "big.txt").write_text("X" * (_MAX_FILE_CHARS + 500), encoding="utf-8")
    result = CodebaseReadTool()._run("big.txt")
    assert "truncated" in result


# ── CodebaseListTool ───────────────────────────────────────────────────────────

def test_list_blocks_path_traversal():
    assert "Access denied" in CodebaseListTool()._run("../../")

def test_list_excludes_pycache(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")
    result = CodebaseListTool()._run("")
    assert "__pycache__" not in result
    assert "main.py" in result

def test_list_returns_error_for_nonexistent_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    result = CodebaseListTool()._run("no_such_dir")
    assert "not found" in result


# ── CodebaseGlobTool ───────────────────────────────────────────────────────────

def test_glob_returns_no_matches_message(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    result = CodebaseGlobTool()._run("**/*.nonexistent", 50)
    assert "No files found" in result

def test_glob_finds_files(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    result = CodebaseGlobTool()._run("*.py", 50)
    assert "a.py" in result
    assert "b.py" in result

def test_glob_truncates_at_max_results(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    for i in range(10):
        (tmp_path / f"file{i}.py").write_text("pass", encoding="utf-8")
    result = CodebaseGlobTool()._run("*.py", 3)
    assert "and 7 more" in result

def test_glob_excludes_pycache(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "_REPO_ROOT", tmp_path)
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "cached.pyc").write_text("", encoding="utf-8")
    (tmp_path / "real.py").write_text("pass", encoding="utf-8")
    result = CodebaseGlobTool()._run("**/*", 50)
    assert "__pycache__" not in result
