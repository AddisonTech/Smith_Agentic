"""
crews/default_crew.py
Default crew: Orchestrator, Researcher, Builder, Critic.

Flow:
  0. [HITL] Plan approval (skipped with --no-hitl)
  1. plan_task      - Orchestrator breaks goal into execution plan
  2. research_task  - Researcher gathers info, saves outputs/research.md
  3. build_task     - Builder produces deliverable, saves outputs/deliverable.md
  4. critique_task  - Critic reviews deliverable, saves outputs/critique.md
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

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.search_tool import WebSearchTool
from tools.web_fetch_tool import WebFetchTool
from tools.target_repo_tools import create_target_repo_tools
from tools.git_tool import GitStatusTool, GitStageTool, GitCommitTool, GitPushTool
from memory.memory_store import create_memory_tools
from crews.hitl import approve_plan
from config.loader import get_crew_model, get_agent_model, get_target_repo


def build_crew(goal: str, config: dict) -> Crew:
    llm_cfg  = config["llm"]
    crew_cfg = config["crew"]
    verbose  = crew_cfg.get("verbose", True)
    base_url = llm_cfg.get("base_url", "http://localhost:11434")
    timeout  = llm_cfg.get("timeout", 600)
    temp     = llm_cfg.get("temperature", 0.7)

    def _llm(model: str) -> LLM:
        return LLM(model=f"ollama/{model}", base_url=base_url, temperature=temp, timeout=timeout)

    default_model = config.get("_model_override") or get_crew_model(config, "default")

    llm_orch  = _llm(get_agent_model(config, "orchestrator") if not config.get("_model_override") else default_model)
    llm_res   = _llm(get_agent_model(config, "researcher")   if not config.get("_model_override") else default_model)
    llm_build = _llm(get_agent_model(config, "builder")      if not config.get("_model_override") else default_model)
    llm_crit  = _llm(get_agent_model(config, "critic")       if not config.get("_model_override") else default_model)

    # ── Tools ─────────────────────────────────────────────────────────────────
    file_read  = FileReadTool()
    file_write = FileWriteTool()
    file_list  = FileListTool()
    web_search = WebSearchTool()
    web_fetch  = WebFetchTool()
    mem_store, mem_query = create_memory_tools(config)

    target_repo = get_target_repo(config)
    if target_repo:
        tr_read, tr_write, tr_list, tr_glob = create_target_repo_tools(target_repo)
        git_status = GitStatusTool(repo_path=target_repo)
        git_stage  = GitStageTool(repo_path=target_repo)
        git_commit = GitCommitTool(repo_path=target_repo)
        git_push   = GitPushTool(repo_path=target_repo)
        researcher_extra = [tr_read, tr_list, tr_glob]
        builder_extra    = [tr_read, tr_write, tr_list, tr_glob, git_status, git_stage, git_commit, git_push]
    else:
        researcher_extra = []
        builder_extra    = []

    # ── Agents ────────────────────────────────────────────────────────────────
    orchestrator = create_orchestrator(llm=llm_orch, tools=[file_list, mem_query], verbose=verbose)
    researcher   = create_researcher(llm=llm_res, tools=[web_search, web_fetch, file_write, file_list, mem_store, mem_query] + researcher_extra, verbose=verbose)
    builder      = create_builder(llm=llm_build, tools=[file_read, file_write, file_list, mem_store, mem_query] + builder_extra, verbose=verbose)
    critic       = create_critic(llm=llm_crit, tools=[file_read, file_write, file_list, mem_query], verbose=verbose)

    # ── HITL Plan Approval ────────────────────────────────────────────────────
    approved_goal = approve_plan(goal, orchestrator, llm_orch, config)

    # ── Tasks ─────────────────────────────────────────────────────────────────
    plan_task     = create_plan_task(orchestrator, approved_goal)
    research_task = create_research_task(researcher, approved_goal, context=[plan_task])
    build_task    = create_build_task(builder, approved_goal, context=[plan_task, research_task])
    critique_task = create_critique_task(critic, approved_goal, context=[plan_task, build_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[orchestrator, researcher, builder, critic],
        tasks=[plan_task, research_task, build_task, critique_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
