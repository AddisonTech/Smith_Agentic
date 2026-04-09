"""
tasks/plan.py
Planning task — Orchestrator breaks the goal into an execution plan.
This is always task 1; all other tasks receive it as context.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_plan_task(orchestrator: Agent, goal: str) -> Task:
    return Task(
        description=(
            f"You have been given the following high-level goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Produce a structured execution plan. It must include:\n\n"
            "1. GOAL RESTATEMENT — Restate the goal in your own words and define "
            "   what 'done' looks like (measurable success criteria).\n"
            "2. RESEARCH REQUIREMENTS — What information must be gathered before "
            "   building? List specific questions the Researcher must answer.\n"
            "3. DELIVERABLE SPECIFICATION — Exactly what must the Builder produce? "
            "   Describe format, scope, and required content.\n"
            "4. CONSTRAINTS & RISKS — Known limitations, edge cases, or things "
            "   that could go wrong. Flag anything that needs special attention.\n"
            "5. EXECUTION ORDER — Ordered list of steps from research to final output.\n\n"
            "Be specific. This plan will be handed directly to a Researcher and a Builder "
            "who will work from it without further clarification."
        ),
        expected_output=(
            "A structured execution plan with five clearly numbered sections: "
            "Goal Restatement, Research Requirements, Deliverable Specification, "
            "Constraints & Risks, and Execution Order. Plain text, no filler."
        ),
        agent=orchestrator,
    )
