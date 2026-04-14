"""
tools/project_file_tool.py
File I/O tools scoped to the Smith_Agentic project root.

These tools allow agents to read and write any file within the project —
agents/, crews/, tasks/, tools/, memory/, config/, etc.

Used by expansion/build crews that need to create or modify project source files.
The tools enforce path safety: no access outside the project root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Project root = two levels up from this file (tools/ → Smith_Agentic/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class _ProjWriteInput(BaseModel):
    filepath: str = Field(
        description=(
            "Path relative to the project root (Smith_Agentic/). "
            "Do NOT include an absolute path or the 'Smith_Agentic/' prefix. "
            "Examples: 'agents/qa_agent.py', 'tasks/qa_task.py', "
            "'crews/default_crew.py', 'memory/compartments.py', 'config/config.yaml'"
        )
    )
    content: str = Field(description="Full file content to write.")


class _ProjReadInput(BaseModel):
    filepath: str = Field(
        description=(
            "Path relative to the project root (Smith_Agentic/). "
            "Examples: 'agents/builder.py', 'crews/default_crew.py', "
            "'tasks/build.py', 'memory/memory_store.py'"
        )
    )


class _ProjListInput(BaseModel):
    dirpath: str = Field(
        default="",
        description=(
            "Directory path relative to project root. "
            "Leave empty for project root. "
            "Examples: 'agents', 'crews', 'tasks', 'tools', 'memory'"
        ),
    )


class ProjectFileWriteTool(BaseTool):
    name: str = "Write Project File"
    description: str = (
        "Write a source file to any directory within the Smith_Agentic project. "
        "Use this to CREATE new agent files, task files, crew files, tool files, "
        "memory modules, and config files. Also use it to MODIFY existing files. "
        "Provide the path RELATIVE to the project root — no absolute paths, "
        "no 'Smith_Agentic/' prefix. "
        "Examples: filepath='agents/qa_agent.py', filepath='crews/default_crew.py', "
        "filepath='tasks/qa_task.py', filepath='memory/compartments.py'"
    )
    args_schema: Type[BaseModel] = _ProjWriteInput

    def _run(self, filepath: str, content: str) -> str:
        target = (_PROJECT_ROOT / filepath).resolve()
        # Prevent path traversal outside project root
        if not str(target).startswith(str(_PROJECT_ROOT)):
            return f"Error: Access denied — '{filepath}' is outside project root."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Written: {filepath} ({len(content):,} chars, {content.count(chr(10))+1} lines)"


class ProjectFileReadTool(BaseTool):
    name: str = "Read Project File"
    description: str = (
        "Read any source file from the Smith_Agentic project. "
        "Use this to read existing agent files, crew files, task files, tools, etc. "
        "Provide path RELATIVE to project root. "
        "Examples: filepath='agents/builder.py', filepath='crews/default_crew.py'"
    )
    args_schema: Type[BaseModel] = _ProjReadInput

    def _run(self, filepath: str) -> str:
        target = (_PROJECT_ROOT / filepath).resolve()
        if not str(target).startswith(str(_PROJECT_ROOT)):
            return f"Error: Access denied — '{filepath}' is outside project root."
        if not target.exists():
            return f"Error: '{filepath}' not found in project."
        if not target.is_file():
            return f"Error: '{filepath}' is a directory."
        content = target.read_text(encoding="utf-8", errors="replace")
        return f"--- {filepath} ---\n{content}"


class ProjectListTool(BaseTool):
    name: str = "List Project Directory"
    description: str = (
        "List files and subdirectories in a Smith_Agentic project directory. "
        "Use this to see what files already exist before creating new ones. "
        "Provide path relative to project root, or leave empty for root listing."
    )
    args_schema: Type[BaseModel] = _ProjListInput

    def _run(self, dirpath: str = "") -> str:
        target = (_PROJECT_ROOT / dirpath).resolve() if dirpath else _PROJECT_ROOT
        if not str(target).startswith(str(_PROJECT_ROOT)):
            return f"Error: Access denied."
        if not target.exists():
            return f"Error: '{dirpath}' not found."
        if not target.is_dir():
            return f"Error: '{dirpath}' is a file."
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for entry in entries:
            if entry.name in ("__pycache__", ".git"):
                continue
            rel = entry.relative_to(_PROJECT_ROOT)
            prefix = "  " if entry.is_file() else "D "
            lines.append(f"{prefix}{rel}")
        return "\n".join(lines) if lines else "Empty directory."
