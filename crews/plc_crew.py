"""
crews/plc_crew.py
PLC-specialized crew for Rockwell/Allen-Bradley Logix development.

Flow:
  0. [HITL] Plan approval
  1. PLCPlanner        — decomposes goal into program structure, I/O tags, AOIs, UDTs
  2. PLCResearcher     — gathers specs, standards refs, checks plc_generator/ for reuse
  3. PLCDeveloper      — writes ladder logic, ST routines, AOIs, L5X stubs
  4. PLCSafetyReviewer — reviews for NFPA 79, fault handling, interlock completeness
  5. PLCDeveloper      — revises per review notes
"""
from __future__ import annotations

from crewai import Crew, LLM, Process

from agents.plc_planner import create_plc_planner
from agents.researcher import create_researcher
from agents.plc_developer import create_plc_developer
from agents.plc_safety_reviewer import create_plc_safety_reviewer

from tasks.plan import create_plan_task
from tasks.research import create_research_task
from tasks.build import create_build_task
from tasks.critique import create_critique_task
from tasks.revise import create_revise_task

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.search_tool import WebSearchTool
from tools.codebase_reader import CodebaseReadTool, CodebaseListTool, CodebaseGlobTool
from memory.memory_store import create_memory_tools
from crews.hitl import approve_plan
from config.loader import get_crew_model


def build_crew(goal: str, config: dict) -> Crew:
    llm_cfg  = config["llm"]
    crew_cfg = config["crew"]
    verbose  = crew_cfg.get("verbose", True)

    model = config.get("_model_override") or get_crew_model(config, "plc")

    llm = LLM(
        model=f"ollama/{model}",
        base_url=llm_cfg.get("base_url", "http://localhost:11434"),
        temperature=llm_cfg.get("temperature", 0.7),
        timeout=llm_cfg.get("timeout", 600),
    )

    # ── Tools ─────────────────────────────────────────────────────────────────
    file_read  = FileReadTool()
    file_write = FileWriteTool()
    file_list  = FileListTool()
    web_search = WebSearchTool()
    cb_read    = CodebaseReadTool()
    cb_list    = CodebaseListTool()
    cb_glob    = CodebaseGlobTool()
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents — dedicated specialized implementations ─────────────────────────
    planner    = create_plc_planner(
        llm=llm,
        tools=[file_list, cb_list, cb_glob, mem_query],
        verbose=verbose,
    )
    researcher = create_researcher(
        llm=llm,
        tools=[web_search, file_write, file_list, cb_read, cb_glob, mem_store, mem_query],
        verbose=verbose,
    )
    developer  = create_plc_developer(
        llm=llm,
        tools=[file_read, file_write, file_list, cb_read, cb_glob, mem_store, mem_query],
        verbose=verbose,
    )
    reviewer   = create_plc_safety_reviewer(
        llm=llm,
        tools=[file_read, file_write, file_list, cb_read, mem_query],
        verbose=verbose,
    )

    # ── HITL + Tasks ──────────────────────────────────────────────────────────
    approved_goal = approve_plan(goal, planner, llm, config)

    plan_task     = create_plan_task(planner, approved_goal)
    research_task = create_research_task(researcher, approved_goal, context=[plan_task])
    build_task    = create_build_task(developer, approved_goal, context=[plan_task, research_task])
    critique_task = create_critique_task(reviewer, approved_goal, context=[plan_task, build_task])
    revise_task   = create_revise_task(developer, approved_goal, context=[plan_task, build_task, critique_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[planner, researcher, developer, reviewer],
        tasks=[plan_task, research_task, build_task, critique_task, revise_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
