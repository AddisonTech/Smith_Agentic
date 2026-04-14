"""
agents/observability_agent.py
Observability Monitor agent — analyzes crew run audit trail, produces telemetry report.
Follows OpenTelemetry span-and-trace conventions for agent run reporting.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_observability_agent(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Observability Monitor",
        goal=(
            "After a crew run completes, analyze the run's audit trail. "
            "Read all output files: research.md, deliverable.md, critique.md, "
            "deliverable_revised.md, qa_report.md (if present), security_report.md (if present), "
            "deploy_report.md (if present). "
            "Produce telemetry_report.md containing: agents that ran and approximate "
            "iterations used, files produced, any SENTINEL_BLOCK / SECURITY_BLOCK / "
            "DEPLOY_BLOCKED verdicts, and recommendations for improving the next run."
        ),
        backstory=(
            "You are a platform engineer and observability specialist who reads agent outputs "
            "and reconstructs what happened during a run. You flag anomalies, repeated failures, "
            "and missing outputs. Your reports help developers tune agent behavior. "
            "You are data-driven: you read every available report before drawing conclusions. "
            "Your recommendations are specific and actionable, not generic advice."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=5,
    )
