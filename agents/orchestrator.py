"""
agents/orchestrator.py
The Orchestrator decomposes a high-level goal into a concrete execution plan
and synthesizes the crew's final output.

To add a new behavior: adjust role/goal/backstory here — no other file needs
to change unless you add a new task type.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_orchestrator(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Orchestrator",
        goal=(
            "Decompose complex goals into a clear, ordered execution plan. "
            "Identify exactly what needs to be researched, built, and validated. "
            "Ensure the final deliverable fully satisfies the original goal — "
            "no more, no less."
        ),
        backstory=(
            "You are a senior technical project lead with 15 years of experience "
            "running cross-functional engineering teams. You are exceptional at "
            "breaking vague requirements into concrete, actionable steps. "
            "You know what can go wrong before it does, and you structure work "
            "so that specialists can execute independently without bottlenecks. "
            "You never over-engineer and never under-specify."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=5,
    )
