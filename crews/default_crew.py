"""
crews/default_crew.py
Default crew: Orchestrator → Researcher → Builder → Critic → Builder (revision)

Flow:
  0. [HITL] Plan approval loop (skipped with --no-hitl)
  1. plan_task     — Orchestrator breaks goal into execution plan
  2. research_task — Researcher gathers info, saves outputs/research.md
  3. build_task    — Builder produces deliverable, saves outputs/deliverable.md
  4. critique_task — Critic reviews, saves outputs/critique.md
  5. revise_task   — Builder revises per critique, saves outputs/deliverable_revised.md
"""
from __future__ import annotations

from crewai import Crew, LLM, Process

from agents.orchestrator import create_orchestrator
from agents.researcher import create_researcher
from agents.builder import create_builder
from agents.critic import create_critic

from tasks.plan import create_plan_task
from tasks.research import create_research_task
from tasks.build import create_build_task
from tasks.critique import create_critique_task
from tasks.revise import create_revise_task

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.search_tool import WebSearchTool
from memory.memory_store import create_memory_tools
from crews.hitl import approve_plan
from config.loader import get_crew_model


def build_crew(goal: str, config: dict) -> Crew:
    llm_cfg  = config["llm"]
    crew_cfg = config["crew"]
    verbose  = crew_cfg.get("verbose", True)

    # CLI --model overrides crew default; otherwise use per-crew assignment
    model = config.get("_model_override") or get_crew_model(config, "default")

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
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents ────────────────────────────────────────────────────────────────
    orchestrator = create_orchestrator(llm=llm, tools=[file_list, mem_query], verbose=verbose)
    researcher   = create_researcher(llm=llm, tools=[web_search, file_write, file_list, mem_store, mem_query], verbose=verbose)
    builder      = create_builder(llm=llm, tools=[file_read, file_write, file_list, mem_store, mem_query], verbose=verbose)
    critic       = create_critic(llm=llm, tools=[file_read, file_write, file_list, mem_query], verbose=verbose)

    # ── HITL Plan Approval ────────────────────────────────────────────────────
    approved_goal = approve_plan(goal, orchestrator, llm, config)

    # ── Tasks ─────────────────────────────────────────────────────────────────
    plan_task     = create_plan_task(orchestrator, approved_goal)
    research_task = create_research_task(researcher, approved_goal, context=[plan_task])
    build_task    = create_build_task(builder, approved_goal, context=[plan_task, research_task])
    critique_task = create_critique_task(critic, approved_goal, context=[plan_task, build_task])
    revise_task   = create_revise_task(builder, approved_goal, context=[plan_task, build_task, critique_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[orchestrator, researcher, builder, critic],
        tasks=[plan_task, research_task, build_task, critique_task, revise_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
