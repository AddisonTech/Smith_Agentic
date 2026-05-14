"""
crews/safety_crew.py
Safety crew: QA Sentinel, Security Reviewer, Deployment Validator.

Run this crew after a deliverable has been produced to validate it for
correctness, security, and deployment readiness.

Flow:
  1. qa_task       - QA Sentinel executes and validates code artifacts
  2. security_task - Security Reviewer audits for vulnerabilities
  3. deploy_task   - Deployment Validator checks compile and import chains

build_safety_agents() is exported so other crews (e.g. plc_crew) can
reuse the same agent setup rather than duplicating it.
"""
from __future__ import annotations

from crewai import Agent, Crew, LLM, Process

from agents.qa_agent import create_qa_agent
from agents.security_agent import create_security_agent
from agents.deploy_agent import create_deploy_agent

from tasks.qa_task import create_qa_task
from tasks.security_task import create_security_task
from tasks.deploy_task import create_deploy_task

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.code_executor import CodeExecutorTool
from memory.memory_store import create_memory_tools
from config.loader import get_crew_model, get_agent_model


def build_safety_agents(
    llm_qa: LLM,
    llm_sec: LLM,
    llm_dep: LLM,
    file_read,
    file_write,
    file_list,
    code_exec,
    mem_store,
    mem_query,
    verbose: bool = True,
) -> tuple[Agent, Agent, Agent]:
    """Return (qa_agent, sec_agent, dep_agent) with their standard tool sets."""
    qa_agent  = create_qa_agent(llm=llm_qa,  tools=[file_read, file_write, file_list, code_exec, mem_store, mem_query], verbose=verbose)
    sec_agent = create_security_agent(llm=llm_sec, tools=[file_read, file_write, file_list, mem_store, mem_query], verbose=verbose)
    dep_agent = create_deploy_agent(llm=llm_dep,  tools=[file_read, file_write, file_list, code_exec, mem_store, mem_query], verbose=verbose)
    return qa_agent, sec_agent, dep_agent


def build_crew(goal: str, config: dict) -> Crew:
    llm_cfg  = config["llm"]
    crew_cfg = config["crew"]
    verbose  = crew_cfg.get("verbose", True)
    base_url = llm_cfg.get("base_url", "http://localhost:11434")
    timeout  = llm_cfg.get("timeout", 600)
    temp     = llm_cfg.get("temperature", 0.7)

    def _llm(model: str) -> LLM:
        return LLM(model=f"ollama/{model}", base_url=base_url, temperature=temp, timeout=timeout)

    default_model = config.get("_model_override") or get_crew_model(config, "safety")
    llm_qa  = _llm(get_agent_model(config, "qa_agent")       if not config.get("_model_override") else default_model)
    llm_sec = _llm(get_agent_model(config, "security_agent") if not config.get("_model_override") else default_model)
    llm_dep = _llm(get_agent_model(config, "deploy_agent")   if not config.get("_model_override") else default_model)

    # ── Tools ─────────────────────────────────────────────────────────────────
    file_read  = FileReadTool()
    file_write = FileWriteTool()
    file_list  = FileListTool()
    code_exec  = CodeExecutorTool()
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents ────────────────────────────────────────────────────────────────
    qa_agent, sec_agent, dep_agent = build_safety_agents(
        llm_qa, llm_sec, llm_dep,
        file_read, file_write, file_list, code_exec, mem_store, mem_query,
        verbose=verbose,
    )

    # ── Tasks (no HITL - safety crew validates existing outputs) ──────────────
    qa_task       = create_qa_task(qa_agent, goal)
    security_task = create_security_task(sec_agent, goal, context=[qa_task])
    deploy_task   = create_deploy_task(dep_agent, goal, context=[qa_task, security_task])

    process = (
        Process.sequential
        if crew_cfg.get("process", "sequential") == "sequential"
        else Process.hierarchical
    )

    return Crew(
        agents=[qa_agent, sec_agent, dep_agent],
        tasks=[qa_task, security_task, deploy_task],
        process=process,
        verbose=verbose,
        max_rpm=crew_cfg.get("max_rpm", 10),
    )
