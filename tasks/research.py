"""
tasks/research.py
Research task — Researcher gathers information based on the plan and saves
findings to outputs/research.md.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_research_task(
    researcher: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Using the execution plan provided in your context, conduct thorough "
            f"research to support this goal:\n\n  GOAL: {goal}\n\n"
            "Your research must cover every question listed in the plan's "
            "Research Requirements section. Structure your findings as:\n\n"
            "1. BACKGROUND — Key concepts, definitions, and domain knowledge\n"
            "2. BEST PRACTICES — Established approaches, patterns, standards\n"
            "3. TOOLS & REFERENCES — Relevant libraries, frameworks, examples, "
            "   documentation links\n"
            "4. PITFALLS — Known failure modes, gotchas, and things to avoid\n"
            "5. SUMMARY — 3–5 bullet points the Builder needs most\n\n"
            "You MUST use the 'Write Output File' tool to save your report — "
            "pass filepath='research.md' (just the filename, not 'outputs/research.md'). "
            "Also return the full report as your output."
        ),
        expected_output=(
            "A structured research report with five sections (Background, Best Practices, "
            "Tools & References, Pitfalls, Summary) saved via the Write Output File tool "
            "with filepath='research.md'. Also returned as task output."
        ),
        agent=researcher,
        context=context or [],
    )
