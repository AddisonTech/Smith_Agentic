"""
tools/target_repo_tools.py
File I/O tools scoped to an arbitrary target repository.
Pass repo_path at construction to point agents at any directory on disk.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ── Schemas ───────────────────────────────────────────────────────────────────

class _ReadInput(BaseModel):
    filepath: str = Field(
        description=(
            "Path relative to the target repo root. "
            "Example: 'app/(tabs)/index.tsx' or 'lib/theme.ts'."
        )
    )


class _WriteInput(BaseModel):
    filepath: str = Field(
        description=(
            "Path relative to the target repo root. "
            "Intermediate directories are created automatically."
        )
    )
    content: str = Field(description="Full content to write to the file.")


class _ListInput(BaseModel):
    subpath: str = Field(
        default="",
        description=(
            "Subdirectory to list, relative to the target repo root. "
            "Leave empty to list the root."
        ),
    )


class _GlobInput(BaseModel):
    pattern: str = Field(
        description=(
            "Glob pattern relative to the target repo root. "
            "Example: '**/*.tsx' or 'app/**/*.ts'."
        )
    )


# ── Tools ─────────────────────────────────────────────────────────────────────

class TargetRepoReadTool(BaseTool):
    name: str = "Read Target Repo File"
    description: str = (
        "Read the full contents of any file inside the target repository. "
        "Use this to inspect source files before making edits."
    )
    args_schema: Type[BaseModel] = _ReadInput
    repo_path: str = ""

    def _run(self, filepath: str) -> str:
        root = Path(self.repo_path).resolve()
        target = (root / filepath).resolve()
        if not str(target).startswith(str(root)):
            return "Error: Access denied — path escapes the target repo root."
        if not target.exists():
            return f"Error: '{filepath}' not found in target repo."
        if not target.is_file():
            return f"Error: '{filepath}' is a directory, not a file."
        return target.read_text(encoding="utf-8", errors="replace")


class TargetRepoWriteTool(BaseTool):
    name: str = "Write Target Repo File"
    description: str = (
        "Write or overwrite a file directly inside the target repository. "
        "Creates intermediate directories as needed. "
        "Use this to apply code changes, patches, or new files to the project."
    )
    args_schema: Type[BaseModel] = _WriteInput
    repo_path: str = ""

    def _run(self, filepath: str, content: str) -> str:
        root = Path(self.repo_path).resolve()
        target = (root / filepath).resolve()
        if not str(target).startswith(str(root)):
            return "Error: Access denied — path escapes the target repo root."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content):,} characters to {filepath}."


class TargetRepoListTool(BaseTool):
    name: str = "List Target Repo Directory"
    description: str = (
        "List files and directories inside a given path within the target repository. "
        "Use this to explore the project structure before reading or writing files."
    )
    args_schema: Type[BaseModel] = _ListInput
    repo_path: str = ""

    def _run(self, subpath: str = "") -> str:
        root = Path(self.repo_path).resolve()
        target = (root / subpath).resolve() if subpath else root
        if not str(target).startswith(str(root)):
            return "Error: Access denied — path escapes the target repo root."
        if not target.exists():
            return f"Error: '{subpath}' does not exist in the target repo."
        if not target.is_dir():
            return f"Error: '{subpath}' is a file, not a directory."
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for entry in entries:
            rel = entry.relative_to(root)
            lines.append(f"{'[dir] ' if entry.is_dir() else '      '}{rel}")
        return "\n".join(lines) if lines else "Directory is empty."


class TargetRepoGlobTool(BaseTool):
    name: str = "Glob Target Repo"
    description: str = (
        "Search the target repository using a glob pattern. "
        "Returns all matching file paths relative to the repo root. "
        "Example patterns: '**/*.tsx', 'app/**/*.ts', 'lib/*.py'."
    )
    args_schema: Type[BaseModel] = _GlobInput
    repo_path: str = ""

    def _run(self, pattern: str) -> str:
        root = Path(self.repo_path).resolve()
        matches = sorted(
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file() and fnmatch.fnmatch(str(p.relative_to(root)), pattern)
        )
        if not matches:
            return f"No files matched pattern '{pattern}'."
        return "\n".join(matches)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_target_repo_tools(repo_path: str) -> tuple[
    TargetRepoReadTool,
    TargetRepoWriteTool,
    TargetRepoListTool,
    TargetRepoGlobTool,
]:
    """Instantiate all four target-repo tools bound to repo_path."""
    return (
        TargetRepoReadTool(repo_path=repo_path),
        TargetRepoWriteTool(repo_path=repo_path),
        TargetRepoListTool(repo_path=repo_path),
        TargetRepoGlobTool(repo_path=repo_path),
    )
