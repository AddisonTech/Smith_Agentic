"""
tasks/build.py
Build task — Builder produces the primary deliverable from the plan and research.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_build_task(
    builder: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Using the execution plan and research in your context, build the "
            f"primary deliverable for this goal:\n\n  GOAL: {goal}\n\n"
            "Requirements:\n"
            "1. Produce a COMPLETE deliverable — not a draft, not a scaffold. "
            "   Every section specified in the plan must be present and finished.\n"
            "2. Incorporate the Researcher's findings — reference them, don't ignore them.\n"
            "3. If the deliverable is code: it must be syntactically correct, "
            "   commented where non-obvious, and include usage instructions.\n"
            "4. If the deliverable is a document: it must be structured, complete, "
            "   and immediately usable by someone who hasn't seen the plan.\n"
            "5. You MUST use the 'Write Output File' tool to save your deliverable — "
            "   pass filepath='deliverable.md' (just the filename, not 'outputs/deliverable.md'). "
            "   Do this BEFORE giving your final answer.\n\n"
            "Do not give your final answer until the file has been written."
        ),
        expected_output=(
            "A complete, production-ready deliverable written via the Write Output File tool "
            "with filepath='deliverable.md'. Also returned as task output in full."
        ),
        agent=builder,
        context=context or [],
    )
