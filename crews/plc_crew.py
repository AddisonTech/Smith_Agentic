"""
crews/plc_crew.py
PLC-specialized crew for Rockwell/Allen-Bradley Logix development.

Flow:
  0. [HITL] Plan approval
  1. PLCPlanner          — decomposes goal into program structure, I/O tags, AOIs, UDTs
  2. PLCResearcher       — gathers specs, standards refs, checks plc_generator/ for reuse
  3. PLCDeveloper        — writes ladder logic, ST routines, AOIs, L5X stubs
  4. PLCSafetyReviewer   — reviews for NFPA 79, fault handling, interlock completeness
  5. PLCDeveloper        — revises per review notes
  6. QA Sentinel         — executes and validates code artifacts
  7. Security Reviewer   — audits for hardcoded credentials and injection risks
  8. Deployment Validator — compile-checks all code artifacts
"""
from __future__ import annotations

from crewai import Crew, LLM, Process

from agents.plc_planner import create_plc_planner
from agents.researcher import create_researcher
from agents.plc_developer import create_plc_developer
from agents.plc_safety_reviewer import create_plc_safety_reviewer
from agents.qa_agent import create_qa_agent
from agents.security_agent import create_security_agent
from agents.deploy_agent import create_deploy_agent

from tasks.plan import create_plan_task
from tasks.research import create_research_task
from tasks.build import create_build_task
from tasks.critique import create_critique_task
from tasks.revise import create_revise_task
from tasks.qa_task import create_qa_task
from tasks.security_task import create_security_task
from tasks.deploy_task import create_deploy_task

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.search_tool import WebSearchTool
from tools.code_executor import CodeExecutorTool
from tools.codebase_reader import CodebaseReadTool, CodebaseListTool, CodebaseGlobTool
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

    model = config.get("_model_override") or get_crew_model(config, "plc")
    llm_main = _llm(model)
    llm_qa   = _llm(get_agent_model(config, "qa_agent")       if not config.get("_model_override") else model)
    llm_sec  = _llm(get_agent_model(config, "security_agent") if not config.get("_model_override") else model)
    llm_dep  = _llm(get_agent_model(config, "deploy_agent")   if not config.get("_model_override") else model)

    # ── Tools ─────────────────────────────────────────────────────────────────
    file_read  = FileReadTool()
    file_write = FileWriteTool()
    file_list  = FileListTool()
    web_search = WebSearchTool()
    code_exec  = CodeExecutorTool()
    cb_read    = CodebaseReadTool()
    cb_list    = CodebaseListTool()
    cb_glob    = CodebaseGlobTool()
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents ────────────────────────────────────────────────────────────────
    planner    = create_plc_planner(llm=llm_main, tools=[file_list, cb_list, cb_glob, mem_query], verbose=verbose)
    researcher = create_researcher(llm=llm_main, tools=[web_search, file_write, file_list, cb_read, cb_glob, mem_store, mem_query], verbose=verbose)
    developer  = create_plc_developer(llm=llm_main, tools=[file_read, file_write, file_list, cb_read, cb_glob, mem_store, mem_query], verbose=verbose)
    reviewer   = create_plc_safety_reviewer(llm=llm_main, tools=[file_read, file_write, file_list, cb_read, mem_query], verbose=verbose)
    qa_agent   = create_qa_agent(llm=llm_qa, tools=[file_read, file_write, file_list, code_exec, mem_store, mem_query], verbose=verbose)
    sec_agent  = create_security_agent(llm=llm_sec, tools=[file_read, file_write, file_list, mem_store, mem_query], verbose=verbose)
    dep_agent  = create_deploy_agent(llm=llm_dep, tools=[file_read, file_write, file_list, code_exec, mem_store, mem_query], verbose=verbose)

    # ── HITL + Tasks ──────────────────────────────────────────────────────────
    approved_goal = approve_plan(goal, planner, llm_main, config)

    plan_task     = create_plan_task(planner, approved_goal)
    research_task = create_research_task(researcher, approved_goal, context=[plan_task])
    build_task    = create_build_task(developer, approved_goal, context=[plan_task, research_task])
    critique_task = create_critique_task(reviewer, approved_goal, context=[plan_task, build_task])
    revise_task   = create_revise_task(developer, approved_goal, context=[plan_task, build_task, critique_task])
    qa_task       = create_qa_task(qa_agent, approved_goal, context=[plan_task, revise_task])
    security_task = create_security_task(sec_agent, approved_goal, context=[plan_task, revise_task])
    deploy_task   = create_deploy_task(dep_agent, approved_goal, context=[plan_task, revise_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[planner, researcher, developer, reviewer, qa_agent, sec_agent, dep_agent],
        tasks=[plan_task, research_task, build_task, critique_task, revise_task, qa_task, security_task, deploy_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
