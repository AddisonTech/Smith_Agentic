"""
tasks/critique.py
Critique task — Critic reviews the deliverable against the goal and plan,
then issues APPROVED or NEEDS REVISION with specific actionable notes.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_critique_task(
    critic: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Review all outputs produced so far against the original goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Use the 'Read Output File' tool to read the files — "
            "pass filepath='deliverable.md' and filepath='research.md' "
            "(just filenames, not 'outputs/...'). Evaluate the deliverable on:\n\n"
            "1. COMPLETENESS — Does it address every part of the goal and plan? "
            "   List any missing sections or requirements.\n"
            "2. CORRECTNESS — Is the content accurate, logical, and consistent? "
            "   Flag any factual errors, contradictions, or unsupported claims.\n"
            "3. QUALITY — Is it clear, well-structured, and ready for use? "
            "   Identify specific passages that are vague, confusing, or incomplete.\n"
            "4. ALIGNMENT WITH RESEARCH — Did the Builder incorporate the research? "
            "   Note gaps between what was researched and what was delivered.\n"
            "5. VERDICT — One of:\n"
            "   - APPROVED: Output meets the goal. No changes required.\n"
            "   - NEEDS REVISION: Output fails on one or more criteria. "
            "     Provide a numbered list of SPECIFIC required changes.\n\n"
            "You MUST use the 'Write Output File' tool to save your critique — "
            "pass filepath='critique.md'. Be precise — "
            "say exactly what is wrong and exactly what needs to change."
        ),
        expected_output=(
            "A structured critique written via Write Output File with filepath='critique.md', "
            "with sections: Completeness, Correctness, Quality, Research Alignment, and Verdict. "
            "Verdict must be either APPROVED or NEEDS REVISION. "
            "If NEEDS REVISION, include a numbered list of specific required changes."
        ),
        agent=critic,
        context=context or [],
    )
