"""
tools/file_tools.py
File I/O tools scoped to the outputs/ directory.
Agents can read, write, and list files — nothing outside outputs/ is accessible.
"""
from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
_OUTPUTS_DIR.mkdir(exist_ok=True)


# ── Schemas ──────────────────────────────────────────────────────────────────

class _ReadInput(BaseModel):
    filepath: str = Field(
        description="Filename only — do NOT include 'outputs/' prefix. "
                    "The tool already scopes to outputs/. "
                    "Correct: 'research.md'. Wrong: 'outputs/research.md'."
    )


class _WriteInput(BaseModel):
    filepath: str = Field(
        description="Filename only — do NOT include 'outputs/' prefix. "
                    "The tool already scopes to outputs/. "
                    "Correct: 'deliverable.md'. Wrong: 'outputs/deliverable.md'."
    )
    content: str = Field(description="Full content to write to the file.")


class _NoArgs(BaseModel):
    pass


# ── Tools ─────────────────────────────────────────────────────────────────────

class FileReadTool(BaseTool):
    name: str = "Read Output File"
    description: str = (
        "Read the full contents of a file from the outputs/ directory. "
        "Use this to read research notes, previous deliverables, or critique files."
    )
    args_schema: Type[BaseModel] = _ReadInput

    def _run(self, filepath: str) -> str:
        target = (_OUTPUTS_DIR / filepath).resolve()
        # Prevent path traversal outside outputs/
        if not str(target).startswith(str(_OUTPUTS_DIR)):
            return "Error: Access denied — path is outside outputs/."
        if not target.exists():
            return f"Error: '{filepath}' not found in outputs/."
        return target.read_text(encoding="utf-8")


class FileWriteTool(BaseTool):
    name: str = "Write Output File"
    description: str = (
        "Write content to a file in the outputs/ directory. "
        "Creates the file if it doesn't exist; overwrites if it does. "
        "Use this to save research reports, deliverables, critiques, and summaries."
    )
    args_schema: Type[BaseModel] = _WriteInput

    def _run(self, filepath: str, content: str) -> str:
        target = (_OUTPUTS_DIR / filepath).resolve()
        if not str(target).startswith(str(_OUTPUTS_DIR)):
            return "Error: Access denied — path is outside outputs/."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Saved {len(content):,} characters to outputs/{filepath}."


class FileListTool(BaseTool):
    name: str = "List Output Files"
    description: str = (
        "List all files currently saved in the outputs/ directory. "
        "Use this to check what has already been produced before reading or writing."
    )
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self, **kwargs) -> str:
        files = sorted(f for f in _OUTPUTS_DIR.rglob("*") if f.is_file() and f.name != ".gitkeep")
        if not files:
            return "outputs/ is empty — nothing has been saved yet."
        return "\n".join(str(f.relative_to(_OUTPUTS_DIR)) for f in files)
