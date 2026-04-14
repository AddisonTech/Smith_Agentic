"""
tasks/docs_task.py
Documentation task — Documentation Writer generates structured docs for the deliverable.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_docs_task(
    docs_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Generate complete documentation for the deliverable. Goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use 'Read Output File' to read deliverable_revised.md "
            "(fall back to deliverable.md if the revised version does not exist).\n"
            "Step 2: Produce a complete documentation file with all of the following:\n"
            "  - ## Overview: what the deliverable does and why it exists\n"
            "  - ## Installation / Setup: how to install dependencies and configure\n"
            "  - ## Usage: step-by-step usage with concrete examples\n"
            "  - ## API Reference: all functions, classes, or endpoints with signatures\n"
            "  - ## Examples: a working quickstart example\n"
            "Step 3: Use 'Write Output File' to save the documentation. "
            "Pass filepath='docs/deliverable_docs.md'.\n\n"
            "Do not give your final answer until the documentation file has been written."
        ),
        expected_output=(
            "outputs/docs/deliverable_docs.md written via Write Output File, "
            "containing complete Overview, Setup, Usage, API Reference, and Examples sections."
        ),
        agent=docs_agent,
        context=context or [],
    )
