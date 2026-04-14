"""
tools/vision_inspect_tool.py
File I/O tools scoped to the Vision_Inspect repository root.

These tools allow the crew to create and modify any file within the Vision_Inspect
project at ../Vision_Inspect/ (sibling of Smith_Agentic/).

Used by the Vision_Inspect build crew to produce the standalone repository.
Path safety is enforced: no access outside the Vision_Inspect root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Vision_Inspect root is a sibling of Smith_Agentic/
_SMITH_ROOT = Path(__file__).resolve().parent.parent          # Smith_Agentic/
_VI_ROOT    = _SMITH_ROOT.parent / "Vision_Inspect"           # ../Vision_Inspect/


class _VIWriteInput(BaseModel):
    filepath: str = Field(
        description=(
            "Path relative to the Vision_Inspect root. "
            "Do NOT include the 'Vision_Inspect/' prefix. "
            "Examples: 'backend/main.py', 'configs/vlm_config.yaml', "
            "'frontend/src/App.tsx', 'README.md', 'training/dataset_template.json', "
            "'backend/pipeline/ingestion.py', 'backend/proxy_metrics.py'"
        )
    )
    content: str = Field(description="Full file content to write.")


class _VIReadInput(BaseModel):
    filepath: str = Field(
        description=(
            "Path relative to Vision_Inspect root. "
            "Examples: 'backend/main.py', 'configs/input_config.yaml', "
            "'backend/vlm_router.py', 'backend/pipeline/ingestion.py'"
        )
    )


class _VIListInput(BaseModel):
    dirpath: str = Field(
        default="",
        description=(
            "Directory path relative to Vision_Inspect root. "
            "Leave empty for root listing. "
            "Examples: 'backend', 'backend/pipeline', 'frontend/src', "
            "'configs', 'training', 'models/versions'"
        ),
    )


class VisionInspectWriteTool(BaseTool):
    name: str = "Write Vision_Inspect File"
    description: str = (
        "Write a source file to any directory within the Vision_Inspect repository. "
        "Use this to CREATE all Vision_Inspect backend, frontend, config, training, "
        "and documentation files. Provide the path RELATIVE to Vision_Inspect root — "
        "no absolute paths, no 'Vision_Inspect/' prefix. "
        "Examples: filepath='backend/main.py', filepath='configs/vlm_config.yaml', "
        "filepath='frontend/src/App.tsx', filepath='README.md', "
        "filepath='backend/pipeline/ingestion.py'"
    )
    args_schema: Type[BaseModel] = _VIWriteInput

    def _run(self, filepath: str, content: str) -> str:
        vi_root = _VI_ROOT.resolve()
        target  = (vi_root / filepath).resolve()
        if not str(target).startswith(str(vi_root)):
            return f"Error: Access denied — '{filepath}' is outside Vision_Inspect root."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return (
            f"Written: {filepath} "
            f"({len(content):,} chars, {content.count(chr(10)) + 1} lines)"
        )


class VisionInspectReadTool(BaseTool):
    name: str = "Read Vision_Inspect File"
    description: str = (
        "Read any source file from the Vision_Inspect repository. "
        "Use this to verify files written during the build, or to read existing files "
        "before modifying them. Provide path RELATIVE to Vision_Inspect root. "
        "Examples: filepath='backend/main.py', filepath='configs/vlm_config.yaml'"
    )
    args_schema: Type[BaseModel] = _VIReadInput

    def _run(self, filepath: str) -> str:
        vi_root = _VI_ROOT.resolve()
        target  = (vi_root / filepath).resolve()
        if not str(target).startswith(str(vi_root)):
            return f"Error: Access denied — '{filepath}' is outside Vision_Inspect root."
        if not target.exists():
            return f"Error: '{filepath}' not found in Vision_Inspect."
        if not target.is_file():
            return f"Error: '{filepath}' is a directory, not a file."
        content = target.read_text(encoding="utf-8", errors="replace")
        return f"--- {filepath} ---\n{content}"


class VisionInspectListTool(BaseTool):
    name: str = "List Vision_Inspect Directory"
    description: str = (
        "List files and subdirectories in a Vision_Inspect directory. "
        "Use this to verify files exist before and after writing them. "
        "Leave dirpath empty for root listing."
    )
    args_schema: Type[BaseModel] = _VIListInput

    def _run(self, dirpath: str = "") -> str:
        vi_root = _VI_ROOT.resolve()
        target  = (vi_root / dirpath).resolve() if dirpath else vi_root
        if not str(target).startswith(str(vi_root)):
            return "Error: Access denied."
        if not target.exists():
            return f"Error: '{dirpath}' not found in Vision_Inspect."
        if not target.is_dir():
            return f"Error: '{dirpath}' is a file, not a directory."
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines   = []
        for entry in entries:
            if entry.name in ("__pycache__", ".git", "node_modules", ".next"):
                continue
            rel    = entry.relative_to(vi_root)
            prefix = "  " if entry.is_file() else "D "
            lines.append(f"{prefix}{rel}")
        return "\n".join(lines) if lines else "Empty directory."
