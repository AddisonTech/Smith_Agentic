"""
crews/ops_crew.py
Ops crew: Documentation Writer, Memory Manager, Observability Monitor.

Run this crew after a deliverable has been produced to generate docs,
consolidate run knowledge into memory, and produce a telemetry report.

Flow:
  1. docs_task          - Documentation Writer generates structured markdown docs
  2. memory_task        - Memory Manager consolidates key findings into ChromaDB
  3. observability_task - Observability Monitor produces telemetry_report.md
"""
from __future__ import annotations

from crewai import Crew, LLM, Process

from agents.docs_agent import create_docs_agent
from agents.memory_agent import create_memory_agent
from agents.observability_agent import create_observability_agent

from tasks.docs_task import create_docs_task
from tasks.memory_task import create_memory_task
from tasks.observability_task import create_observability_task

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from memory.memory_store import create_memory_tools
from crews.hitl import approve_plan
from config.loader import get_crew_model, get_agent_model


def build_crew(goal: str, config: dict) -> Crew:
    llm_cfg  = config["llm"]
    crew_cfg = config["crew"]
    verbose  = crew_cfg.get("verbose", True)
    base_url = llm_cfg.get("base_url", "http://localhost:11434")
    timeout  = llm_cfg.get("timeout", 600)
    temp     = llm_cfg.get("temperature", 0.7)

    def _llm(model: str) -> LLM:
        return LLM(model=f"ollama/{model}", base_url=base_url, temperature=temp, timeout=timeout)

    default_model = config.get("_model_override") or get_crew_model(config, "ops")
    llm_docs = _llm(get_agent_model(config, "docs_agent")          if not config.get("_model_override") else default_model)
    llm_mem  = _llm(get_agent_model(config, "memory_agent")        if not config.get("_model_override") else default_model)
    llm_obs  = _llm(get_agent_model(config, "observability_agent") if not config.get("_model_override") else default_model)

    # ── Tools ─────────────────────────────────────────────────────────────────
    file_read  = FileReadTool()
    file_write = FileWriteTool()
    file_list  = FileListTool()
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents ────────────────────────────────────────────────────────────────
    docs_agent = create_docs_agent(llm=llm_docs, tools=[file_read, file_write, file_list, mem_store, mem_query], verbose=verbose)
    mem_agent  = create_memory_agent(llm=llm_mem,  tools=[file_read, file_list, file_write, mem_store, mem_query], verbose=verbose)
    obs_agent  = create_observability_agent(llm=llm_obs,  tools=[file_read, file_list, file_write, mem_query], verbose=verbose)

    # ── HITL + Tasks ──────────────────────────────────────────────────────────
    approved_goal = approve_plan(goal, docs_agent, llm_docs, config)

    docs_task          = create_docs_task(docs_agent, approved_goal)
    memory_task        = create_memory_task(mem_agent, approved_goal, context=[docs_task])
    observability_task = create_observability_task(obs_agent, approved_goal, context=[docs_task, memory_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[docs_agent, mem_agent, obs_agent],
        tasks=[docs_task, memory_task, observability_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
