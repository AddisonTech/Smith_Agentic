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
            "Research Requirements section.\n\n"
            "REQUIRED research workflow:\n"
            "1. Use 'Web Search' to find relevant sources (run multiple targeted queries).\n"
            "2. For each search, use 'Fetch Web Page' on the top 2-3 result URLs to retrieve "
            "   the FULL article content — do not rely on search snippets alone.\n"
            "3. Synthesize findings from the full page content into your report. "
            "   Cite real URLs from pages you fetched.\n\n"
            "Structure your findings as:\n\n"
            "1. BACKGROUND — Key concepts, definitions, and domain knowledge\n"
            "2. BEST PRACTICES — Established approaches, patterns, standards\n"
            "3. TOOLS & REFERENCES — Relevant libraries, frameworks, examples, "
            "   documentation links with real URLs\n"
            "4. PITFALLS — Known failure modes, gotchas, and things to avoid\n"
            "5. SUMMARY — 3–5 bullet points the Builder needs most\n\n"
            "CRITICAL: You MUST use the 'Write Output File' tool to save your report. "
            "The filepath MUST be exactly 'research.md' — nothing else. "
            "Not 'outputs/research.md', not any other name. Exactly: 'research.md'. "
            "This is non-negotiable. Overwrite it if it already exists. "
            "Do NOT create any other files during this task. "
            "Also return the full report as your task output."
        ),
        expected_output=(
            "A structured research report with five sections (Background, Best Practices, "
            "Tools & References, Pitfalls, Summary) saved via the Write Output File tool "
            "with filepath='research.md'. Also returned as task output."
        ),
        agent=researcher,
        context=context or [],
    )
