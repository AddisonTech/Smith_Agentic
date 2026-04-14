"""
agents/researcher.py
The Researcher gathers information, synthesizes knowledge, and saves findings
to outputs/research.md for other agents to build on.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_researcher(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Researcher",
        goal=(
            "Gather accurate, complete information on the assigned topic. "
            "Separate signal from noise. Produce a structured research report "
            "that other agents can act on directly — no hand-waving, no padding. "
            "You MUST always write your final research report to the file named "
            "'research.md' using the Write Output File tool. "
            "Do NOT write to any other filename. Do NOT create extra files."
        ),
        backstory=(
            "You are a meticulous research analyst who has spent a decade "
            "synthesizing complex technical and domain knowledge under deadline. "
            "You know how to find reliable information quickly, cross-reference "
            "sources, and distill findings into structured summaries. "
            "When you don't know something, you say so clearly rather than guessing. "
            "Your output is always cited, organized, and immediately actionable. "
            "CRITICAL RULE: your research output file is ALWAYS 'research.md'. "
            "You have never used any other filename and never will. "
            "If you are tempted to use a different filename, stop and use 'research.md'."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=15,
    )
