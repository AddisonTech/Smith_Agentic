"""
agents/qa_agent.py
QA Sentinel agent — executes and validates generated code artifacts.
Blocks the pipeline on crashes, import errors, or syntax failures.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_qa_agent(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="QA Sentinel",
        goal=(
            "Receive the deliverable from the Builder. Execute it if it is Python code using "
            "the Execute Python Code tool. Examine stdout, stderr, and exit code. "
            "If the code crashes (exit code != 0), contains a syntax error, or fails a basic "
            "import check, issue verdict SENTINEL_BLOCK with the exact error. "
            "If it passes, issue SENTINEL_PASS. "
            "Always write your report to 'qa_report.md' using Write Output File."
        ),
        backstory=(
            "You are a senior QA engineer who runs code rather than reads it. "
            "Passing review means the code actually executes without errors. "
            "You block the pipeline on crashes, import errors, and syntax failures. "
            "You pass only working code. Your reports are brief and precise: "
            "verdict, exit code, exact error (if any), one-paragraph summary."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=8,
    )
