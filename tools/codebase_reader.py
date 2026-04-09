"""
tools/codebase_reader.py
Read files from the local codebase (repo root and below).

Agents can read any file by path relative to the repo root, list a
directory's contents, or search for files matching a glob pattern.

Safety: all paths are resolved and must remain within the repo root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Repo root = three levels up from this file (smith_agentic/tools/ → repo root)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MAX_FILE_CHARS = 20_000  # cap large files to avoid flooding agent context


class _ReadInput(BaseModel):
    path: str = Field(
        description=(
            "Path to the file to read, relative to the repo root. "
            "Example: '00_Rockwell-Logix/04_AI_Sandbox/smith_agentic/main.py'"
        )
    )


class _ListInput(BaseModel):
    path: str = Field(
        default="",
        description=(
            "Directory path relative to repo root. "
            "Leave empty to list the repo root. "
            "Example: '00_Rockwell-Logix/04_AI_Sandbox'"
        ),
    )


class _GlobInput(BaseModel):
    pattern: str = Field(
        description=(
            "Glob pattern relative to repo root. "
            "Examples: '**/*.py', '04_AI_Sandbox/**/*.js', 'smith_agentic/crews/*.py'"
        )
    )
    max_results: int = Field(default=50, description="Max files to return (default: 50).")


class CodebaseReadTool(BaseTool):
    name: str = "Read Codebase File"
    description: str = (
        "Read the full content of any file in the local codebase. "
        "Provide the path relative to the repo root. "
        "Use this to understand existing code before modifying or extending it."
    )
    args_schema: Type[BaseModel] = _ReadInput

    def _run(self, path: str) -> str:
        target = (_REPO_ROOT / path).resolve()
        if not str(target).startswith(str(_REPO_ROOT)):
            return "Error: Access denied — path is outside the repo root."
        if not target.exists():
            return f"Error: '{path}' not found."
        if not target.is_file():
            return f"Error: '{path}' is a directory, not a file."
        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > _MAX_FILE_CHARS:
            content = content[:_MAX_FILE_CHARS] + f"\n... (truncated at {_MAX_FILE_CHARS} chars)"
        return f"--- {path} ---\n{content}"


class CodebaseListTool(BaseTool):
    name: str = "List Codebase Directory"
    description: str = (
        "List files and subdirectories within a directory of the local codebase. "
        "Helps you discover what exists before reading specific files."
    )
    args_schema: Type[BaseModel] = _ListInput

    def _run(self, path: str = "") -> str:
        target = (_REPO_ROOT / path).resolve() if path else _REPO_ROOT
        if not str(target).startswith(str(_REPO_ROOT)):
            return "Error: Access denied — path is outside the repo root."
        if not target.exists():
            return f"Error: '{path}' not found."
        if not target.is_dir():
            return f"Error: '{path}' is a file, not a directory."
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for entry in entries[:100]:
            rel = entry.relative_to(_REPO_ROOT)
            prefix = "  " if entry.is_file() else "D "
            lines.append(f"{prefix}{rel}")
        if len(list(target.iterdir())) > 100:
            lines.append("... (truncated at 100 entries)")
        return "\n".join(lines) if lines else "Empty directory."


class CodebaseGlobTool(BaseTool):
    name: str = "Glob Codebase Files"
    description: str = (
        "Find files in the codebase matching a glob pattern. "
        "Returns paths relative to repo root. "
        "Useful for finding all Python files, all React components, etc."
    )
    args_schema: Type[BaseModel] = _GlobInput

    def _run(self, pattern: str, max_results: int = 50) -> str:
        matches = sorted(_REPO_ROOT.glob(pattern))
        # Filter out __pycache__ and .git
        matches = [
            m for m in matches
            if "__pycache__" not in m.parts and ".git" not in m.parts and m.is_file()
        ]
        if not matches:
            return f"No files found matching '{pattern}'."
        results = [str(m.relative_to(_REPO_ROOT)) for m in matches[:max_results]]
        suffix = f"\n... and {len(matches) - max_results} more" if len(matches) > max_results else ""
        return f"Found {len(matches)} file(s) matching '{pattern}':\n" + "\n".join(results) + suffix
