"""
crews/vision_crew.py
Vision Inspection crew - orchestrates the Vision_Inspect backend for automated
defect analysis, report generation, and pipeline QA.

Requires the Vision_Inspect FastAPI service running at http://localhost:8000.
Start it with: cd ../Vision_Inspect && uvicorn backend.main:app --port 8000

Flow:
  1. Vision Analyst     - queries /inspections, parses defect results, writes vision_findings.md
  2. Vision Reporter    - synthesizes findings + memory trends, writes inspection_report.md
  3. Vision QA Validator - health-checks API, audits report, flags anomalies, writes vision_qa_report.md
"""
from __future__ import annotations

from crewai import Crew, LLM, Process

from agents.vision_analyst import create_vision_analyst
from agents.vision_reporter import create_vision_reporter
from agents.vision_qa import create_vision_qa

from tasks.vision_tasks import (
    create_vision_analysis_task,
    create_vision_report_task,
    create_vision_qa_task,
)

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.vision_inspect_tool import VisionInspectAPITool
from memory.memory_store import create_memory_tools
from config.loader import get_crew_model, get_agent_model


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
