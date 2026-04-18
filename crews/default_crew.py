"""
crews/default_crew.py
Default crew: full expanded pipeline with Reflexion loop and all specialist agents.

Flow:
  0. [HITL] Plan approval loop (skipped with --no-hitl)
  1.  plan_task          — Orchestrator breaks goal into execution plan
  2.  research_task      — Researcher gathers info, saves outputs/research.md
  3.  build_task         — Builder produces deliverable, saves outputs/deliverable.md
  4.  critique_task      — Critic reviews, saves outputs/critique.md
  5.  revise_task        — Builder revises per critique (Reflexion round 1)
  6.  critique_task2     — Critic re-reviews revised output
  7.  revise_task2       — Builder applies second revision (Reflexion round 2)
  8.  qa_task            — QA Sentinel executes code, issues SENTINEL_PASS/BLOCK
  9.  security_task      — Security Reviewer audits, issues SECURITY_PASS/BLOCK
  10. deploy_task        — Deployment Validator compile-checks, issues DEPLOY_READY/BLOCKED
  11. docs_task          — Documentation Writer generates structured docs
  12. memory_task        — Memory Manager consolidates run into persistent memory
  13. observability_task — Observability Monitor produces telemetry report
"""
from __future__ import annotations

from crewai import Crew, LLM, Process

from agents.orchestrator import create_orchestrator
from agents.researcher import create_researcher
from agents.builder import create_builder
from agents.critic import create_critic
from agents.qa_agent import create_qa_agent
from agents.security_agent import create_security_agent
from agents.deploy_agent import create_deploy_agent
from agents.docs_agent import create_docs_agent
from agents.memory_agent import create_memory_agent
from agents.observability_agent import create_observability_agent

from tasks.plan import create_plan_task
from tasks.research import create_research_task
from tasks.build import create_build_task
from tasks.critique import create_critique_task
from tasks.revise import create_revise_task
from tasks.qa_task import create_qa_task
from tasks.security_task import create_security_task
from tasks.deploy_task import create_deploy_task
from tasks.docs_task import create_docs_task
from tasks.memory_task import create_memory_task
from tasks.observability_task import create_observability_task

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.search_tool import WebSearchTool
from tools.web_fetch_tool import WebFetchTool
from tools.code_executor import CodeExecutorTool
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

    # CLI --model overrides crew default; otherwise use per-crew assignment
    default_model = config.get("_model_override") or get_crew_model(config, "default")

    # ── Per-agent LLM instances ────────────────────────────────────────────────
    llm_orch  = _llm(get_agent_model(config, "orchestrator") if not config.get("_model_override") else default_model)
    llm_res   = _llm(get_agent_model(config, "researcher")   if not config.get("_model_override") else default_model)
    llm_build = _llm(get_agent_model(config, "builder")      if not config.get("_model_override") else default_model)
    llm_crit  = _llm(get_agent_model(config, "critic")       if not config.get("_model_override") else default_model)
    llm_qa    = _llm(get_agent_model(config, "qa_agent")     if not config.get("_model_override") else default_model)
    llm_sec   = _llm(get_agent_model(config, "security_agent") if not config.get("_model_override") else default_model)
    llm_dep   = _llm(get_agent_model(config, "deploy_agent") if not config.get("_model_override") else default_model)
    llm_docs  = _llm(get_agent_model(config, "docs_agent")   if not config.get("_model_override") else default_model)
    llm_mem   = _llm(get_agent_model(config, "memory_agent") if not config.get("_model_override") else default_model)
    llm_obs   = _llm(get_agent_model(config, "observability_agent") if not config.get("_model_override") else default_model)

    # ── Tools ─────────────────────────────────────────────────────────────────
    file_read    = FileReadTool()
    file_write   = FileWriteTool()
    file_list    = FileListTool()
    web_search   = WebSearchTool()
    web_fetch    = WebFetchTool()
    code_exec    = CodeExecutorTool()
    mem_store, mem_query = create_memory_tools(config)

    # Target repo tools (only when --target-repo is provided)
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
    orchestrator  = create_orchestrator(llm=llm_orch, tools=[file_list, mem_query], verbose=verbose)
    researcher    = create_researcher(llm=llm_res, tools=[web_search, web_fetch, file_write, file_list, mem_store, mem_query] + researcher_extra, verbose=verbose)
    builder       = create_builder(llm=llm_build, tools=[file_read, file_write, file_list, mem_store, mem_query] + builder_extra, verbose=verbose)
    critic        = create_critic(llm=llm_crit, tools=[file_read, file_write, file_list, mem_query], verbose=verbose)
    qa_agent      = create_qa_agent(llm=llm_qa, tools=[file_read, file_write, file_list, code_exec, mem_store, mem_query], verbose=verbose)
    security_agent = create_security_agent(llm=llm_sec, tools=[file_read, file_write, file_list, mem_store, mem_query], verbose=verbose)
    deploy_agent  = create_deploy_agent(llm=llm_dep, tools=[file_read, file_write, file_list, code_exec, mem_store, mem_query], verbose=verbose)
    docs_agent    = create_docs_agent(llm=llm_docs, tools=[file_read, file_write, file_list, mem_store, mem_query], verbose=verbose)
    memory_agent  = create_memory_agent(llm=llm_mem, tools=[file_read, file_list, file_write, mem_store, mem_query], verbose=verbose)
    obs_agent     = create_observability_agent(llm=llm_obs, tools=[file_read, file_list, file_write, mem_query], verbose=verbose)

    # ── HITL Plan Approval ────────────────────────────────────────────────────
    approved_goal = approve_plan(goal, orchestrator, llm_orch, config)

    # ── Tasks — Reflexion Loop (2 critique/revise rounds) ────────────────────
    plan_task      = create_plan_task(orchestrator, approved_goal)
    research_task  = create_research_task(researcher, approved_goal, context=[plan_task])
    build_task     = create_build_task(builder, approved_goal, context=[plan_task, research_task])
    critique_task  = create_critique_task(critic, approved_goal, context=[plan_task, build_task])
    revise_task    = create_revise_task(builder, approved_goal, context=[plan_task, build_task, critique_task])
    critique_task2 = create_critique_task(critic, approved_goal, context=[plan_task, revise_task])
    revise_task2   = create_revise_task(builder, approved_goal, context=[plan_task, build_task, critique_task2])

    # ── Tasks — Specialist Pipeline ────────────────────────────────────────────
    qa_task      = create_qa_task(qa_agent, approved_goal, context=[plan_task, revise_task2])
    security_task = create_security_task(security_agent, approved_goal, context=[plan_task, revise_task2])
    deploy_task  = create_deploy_task(deploy_agent, approved_goal, context=[plan_task, revise_task2])
    docs_task    = create_docs_task(docs_agent, approved_goal, context=[plan_task, revise_task2])
    memory_task  = create_memory_task(memory_agent, approved_goal, context=[plan_task, research_task, revise_task2])
    obs_task     = create_observability_task(obs_agent, approved_goal, context=[plan_task, qa_task, security_task, deploy_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[
            orchestrator, researcher, builder, critic,
            qa_agent, security_agent, deploy_agent,
            docs_agent, memory_agent, obs_agent,
        ],
        tasks=[
            plan_task, research_task, build_task,
            critique_task, revise_task,
            critique_task2, revise_task2,
            qa_task, security_task, deploy_task,
            docs_task, memory_task, obs_task,
        ],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
