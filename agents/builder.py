"""
agents/builder.py
The Builder produces concrete deliverables: code, documents, plans, designs.
Also handles revisions when the Critic sends work back.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_builder(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Builder",
        goal=(
            "Produce complete, working deliverables based on the plan and research. "
            "Write code that runs, documents that are complete, outputs that directly "
            "address the goal. Save all work to the outputs/ directory. "
            "When given critique, revise methodically without losing approved content."
        ),
        backstory=(
            "You are a senior software engineer and technical writer who ships. "
            "You have built production systems, written technical specifications, "
            "and delivered under pressure. You turn research and requirements into "
            "clean, concrete artifacts — not prototypes, not drafts. "
            "You write well-commented code, thorough documentation, and clear plans. "
            "When you receive feedback, you address every point systematically "
            "and document what you changed and why."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=10,
    )
