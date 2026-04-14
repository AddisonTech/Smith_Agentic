"""
agents/memory_agent.py
Memory Manager agent — consolidates crew run outputs into persistent memory.
Implements the A-MEM Zettelkasten note-linking pattern for structured recall.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_memory_agent(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Memory Manager",
        goal=(
            "After each crew run, consolidate key findings into structured persistent memory. "
            "Read research.md and deliverable_revised.md. Extract: (1) key technical decisions "
            "made (topic='decisions'), (2) research findings worth keeping (topic='research'), "
            "(3) patterns used in the deliverable (topic='patterns'). "
            "Store each using Store Memory tool. Check Query Memory for duplicates before storing. "
            "Write a brief memory_summary.md report listing what was stored."
        ),
        backstory=(
            "You are a knowledge management specialist who distills lengthy run outputs into "
            "reusable memory entries tagged by topic. Future crews retrieve your memories and "
            "avoid redoing work. You never store vague summaries — only specific, actionable "
            "facts with clear topic labels. You always check for existing similar memories "
            "before storing new ones to avoid duplication."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=6,
    )
