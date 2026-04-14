"""
tasks/observability_task.py
Observability task — Observability Monitor analyzes the full run audit trail.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_observability_task(
    observability_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Generate a run telemetry report for this goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use 'List Output Files' to enumerate available output files.\n"
            "Step 2: Read each of the following that exists using 'Read Output File':\n"
            "  research.md, deliverable.md, critique.md, deliverable_revised.md,\n"
            "  qa_report.md, security_report.md, deploy_report.md\n"
            "Step 3: Use 'Write Output File' to write telemetry_report.md with these sections:\n"
            "  - AGENTS: which agents ran and their estimated iteration counts\n"
            "  - FILES_PRODUCED: complete list of output files created this run\n"
            "  - VERDICTS: any SENTINEL_BLOCK / SECURITY_BLOCK / DEPLOY_BLOCKED verdicts found\n"
            "  - ANOMALIES: missing expected outputs or signs of repeated failure\n"
            "  - RECOMMENDATIONS: 3-5 specific suggestions to improve the next run\n\n"
            "Do not give your final answer until telemetry_report.md has been written."
        ),
        expected_output=(
            "outputs/telemetry_report.md written via Write Output File with "
            "sections: AGENTS, FILES_PRODUCED, VERDICTS, ANOMALIES, RECOMMENDATIONS."
        ),
        agent=observability_agent,
        context=context or [],
    )
