"""
tasks/revise.py
Revision task — Builder reads the Critic's notes and produces an improved
deliverable addressing every flagged issue.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_revise_task(
    builder: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"The Critic has reviewed your deliverable for this goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use the 'Read Output File' tool to read the critique — filepath='critique.md'.\n"
            "Step 2: Use the 'Read Output File' tool to read the deliverable — filepath='deliverable.md'.\n"
            "Step 3: Revise the deliverable to address every issue in the critique.\n\n"
            "Revision rules:\n"
            "1. Address every numbered item in the critique — do not skip any.\n"
            "2. Do not remove or regress content the Critic did not flag.\n"
            "3. If a critique point is ambiguous, make a reasonable interpretation "
            "   and note your interpretation inline.\n"
            "4. Preserve the original structure unless the Critic specifically asked "
            "   you to restructure.\n\n"
            "You MUST use the 'Write Output File' tool to save both files — "
            "filepath='deliverable_revised.md' and filepath='revision_summary.md' "
            "(just filenames, not 'outputs/...'). Do this BEFORE giving your final answer."
        ),
        expected_output=(
            "A revised deliverable written via Write Output File with filepath='deliverable_revised.md' "
            "and a revision summary with filepath='revision_summary.md'. "
            "The revision summary must address every critique item by number. "
            "Return the revised deliverable as task output."
        ),
        agent=builder,
        context=context or [],
    )
