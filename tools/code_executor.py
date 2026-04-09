"""
tools/code_executor.py
Execute Python code snippets in a subprocess and return stdout/stderr.

Safety:
  - Runs in a temporary directory (no access to project files unless explicitly passed)
  - Hard timeout of 30 seconds (configurable)
  - stdout+stderr capped at 8000 chars to prevent flooding agent context
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_MAX_OUTPUT = 8000
_DEFAULT_TIMEOUT = 30  # seconds


class _ExecInput(BaseModel):
    code: str = Field(description="Python code to execute. Must be a complete, runnable script.")
    timeout: int = Field(
        default=_DEFAULT_TIMEOUT,
        description=f"Max seconds to allow execution (default: {_DEFAULT_TIMEOUT}).",
    )


class CodeExecutorTool(BaseTool):
    name: str = "Execute Python Code"
    description: str = (
        "Execute a Python code snippet and return its stdout + stderr output. "
        "Use this to run tests, verify logic, or produce computed results. "
        "The code runs in a temporary directory. Do not rely on local project files unless "
        "you include all needed data inline."
    )
    args_schema: Type[BaseModel] = _ExecInput

    def _run(self, code: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "script.py"
            script.write_text(code, encoding="utf-8")

            try:
                result = subprocess.run(
                    [sys.executable, str(script)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                )
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                rc = result.returncode

                output_parts = []
                if stdout:
                    output_parts.append(f"[stdout]\n{stdout}")
                if stderr:
                    output_parts.append(f"[stderr]\n{stderr}")
                output_parts.append(f"[exit code] {rc}")

                full_output = "\n".join(output_parts)
                if len(full_output) > _MAX_OUTPUT:
                    full_output = full_output[:_MAX_OUTPUT] + f"\n... (truncated at {_MAX_OUTPUT} chars)"
                return full_output

            except subprocess.TimeoutExpired:
                return f"[TIMEOUT] Execution exceeded {timeout}s limit."
            except Exception as e:
                return f"[ERROR] Failed to execute: {e}"
