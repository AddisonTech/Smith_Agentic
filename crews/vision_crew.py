"""
crews/vision_crew.py
Vision Inspection crew — orchestrates the Vision_Inspect backend for automated
defect analysis, report generation, and pipeline QA.

Requires the Vision_Inspect FastAPI service running at http://localhost:8000.
Start it with: cd ../Vision_Inspect && uvicorn backend.main:app --port 8000

Flow:
  1. Vision Analyst     — queries /inspections, parses defect results, writes vision_findings.md
  2. Vision Reporter    — synthesizes findings + memory trends, writes inspection_report.md
  3. Vision QA Validator — health-checks API, audits report, flags anomalies, writes vision_qa_report.md
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Type

import httpx
from crewai import Crew, LLM, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from agents.vision_analyst import create_vision_analyst
from agents.vision_reporter import create_vision_reporter
from agents.vision_qa import create_vision_qa

from tasks.vision_tasks import (
    create_vision_analysis_task,
    create_vision_report_task,
    create_vision_qa_task,
)

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from memory.memory_store import create_memory_tools
from config.loader import get_crew_model, get_agent_model


# ── Vision Inspect API Tool ───────────────────────────────────────────────────

class _APIInput(BaseModel):
    method: str = Field(
        default="GET",
        description="HTTP method: GET or POST.",
    )
    path: str = Field(
        description=(
            "API path relative to the Vision_Inspect base URL. "
            "Examples: '/health', '/inspections', '/inspections/latest', "
            "'/models', '/reports'. Do NOT include the host."
        )
    )
    payload: str = Field(
        default="",
        description=(
            "JSON body as a string for POST requests. Leave empty for GET. "
            "Example: '{\"limit\": 50}'"
        ),
    )


class VisionInspectAPITool(BaseTool):
    """Calls the Vision_Inspect FastAPI backend at http://localhost:8000."""

    name: str = "Call Vision Inspect API"
    description: str = (
        "Call the Vision_Inspect REST API. Use for: health checks (/health), "
        "fetching inspection results (/inspections, /inspections/latest), "
        "listing loaded models (/models), and retrieving reports (/reports). "
        "Specify 'method' (GET/POST), 'path' (relative, e.g. '/health'), "
        "and optional 'payload' (JSON string for POST bodies). "
        "Returns the JSON response as a formatted string."
    )
    args_schema: Type[BaseModel] = _APIInput

    base_url: str = "http://localhost:8000"
    timeout: float = 30.0

    def _run(self, method: str = "GET", path: str = "/health", payload: str = "") -> str:
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method.upper() == "POST":
                    body = json.loads(payload) if payload.strip() else {}
                    resp = client.post(url, json=body)
                else:
                    resp = client.get(url)
            resp.raise_for_status()
            try:
                data = resp.json()
                return json.dumps(data, indent=2)
            except Exception:
                return resp.text
        except httpx.ConnectError:
            return (
                f"Error: Cannot connect to Vision_Inspect at {self.base_url}. "
                "Ensure 'uvicorn backend.main:app --port 8000' is running in "
                "the Vision_Inspect directory."
            )
        except httpx.HTTPStatusError as exc:
            return f"Error: HTTP {exc.response.status_code} — {exc.response.text}"
        except Exception as exc:  # noqa: BLE001
            return f"Error: {type(exc).__name__}: {exc}"


# ── Crew builder ──────────────────────────────────────────────────────────────

def build_crew(goal: str, config: dict) -> Crew:
    llm_cfg  = config["llm"]
    crew_cfg = config["crew"]
    vi_cfg   = config.get("vision_inspect", {})

    verbose  = crew_cfg.get("verbose", True)
    base_url = llm_cfg.get("base_url", "http://localhost:11434")
    timeout  = llm_cfg.get("timeout", 600)
    temp     = llm_cfg.get("temperature", 0.7)

    vi_base_url = vi_cfg.get("base_url", "http://localhost:8000")
    vi_timeout  = float(vi_cfg.get("timeout", 30))

    def _llm(model: str) -> LLM:
        return LLM(model=f"ollama/{model}", base_url=base_url, temperature=temp, timeout=timeout)

    model          = config.get("_model_override") or get_crew_model(config, "vision")
    llm_analyst    = _llm(get_agent_model(config, "vision_analyst")   if not config.get("_model_override") else model)
    llm_reporter   = _llm(get_agent_model(config, "vision_reporter")  if not config.get("_model_override") else model)
    llm_qa         = _llm(get_agent_model(config, "vision_qa")        if not config.get("_model_override") else model)

    # ── Tools ──────────────────────────────────────────────────────────────────
    file_read   = FileReadTool()
    file_write  = FileWriteTool()
    file_list   = FileListTool()
    vi_api      = VisionInspectAPITool(base_url=vi_base_url, timeout=vi_timeout)
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents ─────────────────────────────────────────────────────────────────
    analyst  = create_vision_analyst(
        llm=llm_analyst,
        tools=[vi_api, file_write, file_list, mem_query],
        verbose=verbose,
    )
    reporter = create_vision_reporter(
        llm=llm_reporter,
        tools=[file_read, file_write, mem_store, mem_query],
        verbose=verbose,
    )
    qa       = create_vision_qa(
        llm=llm_qa,
        tools=[vi_api, file_read, file_write, mem_query],
        verbose=verbose,
    )

    # ── Tasks ──────────────────────────────────────────────────────────────────
    analysis_task = create_vision_analysis_task(analyst, goal)
    report_task   = create_vision_report_task(reporter, goal, context=[analysis_task])
    qa_task       = create_vision_qa_task(qa, goal, context=[analysis_task, report_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[analyst, reporter, qa],
        tasks=[analysis_task, report_task, qa_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
