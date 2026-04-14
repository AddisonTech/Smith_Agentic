"""
tasks/memory_task.py
Memory consolidation task — Memory Manager stores key run findings to persistent memory.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_memory_task(
    memory_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Consolidate this crew run into persistent memory. Goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use 'Read Output File' to read research.md.\n"
            "Step 2: Use 'Read Output File' to read deliverable_revised.md "
            "(fall back to deliverable.md if needed).\n"
            "Step 3: Use 'Query Memory' to check for existing similar entries before storing.\n"
            "Step 4: Use 'Store Memory' to save three entries:\n"
            "  - Key technical decisions made during this run (topic='decisions')\n"
            "  - Notable research findings worth preserving (topic='research')\n"
            "  - Patterns and approaches used in the deliverable (topic='patterns')\n"
            "Step 5: Use 'Write Output File' to write memory_summary.md listing what was stored, "
            "with one line per entry showing topic and a short description.\n\n"
            "Do not give your final answer until memory_summary.md has been written."
        ),
        expected_output=(
            "Three memory entries stored and memory_summary.md written via Write Output File, "
            "listing each stored entry with its topic and a one-line description."
        ),
        agent=memory_agent,
        context=context or [],
    )
