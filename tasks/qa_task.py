"""
tasks/qa_task.py
QA validation task — QA Sentinel executes and validates the deliverable.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_qa_task(
    qa_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Run a QA validation pass on the deliverable for this goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use 'Read Output File' to read deliverable_revised.md "
            "(fall back to deliverable.md if the revised version does not exist).\n"
            "Step 2: If the deliverable contains Python code, extract each code block "
            "and execute it using the 'Execute Python Code' tool.\n"
            "Step 3: Parse the exit code and stderr from execution.\n"
            "Step 4: Use 'Write Output File' to write qa_report.md with:\n"
            "  - VERDICT: SENTINEL_PASS or SENTINEL_BLOCK\n"
            "  - EXIT_CODE: (the exit code from execution)\n"
            "  - ERRORS: (exact stderr output, or 'None')\n"
            "  - SUMMARY: one paragraph describing what was tested and the result\n\n"
            "Do not give your final answer until qa_report.md has been written."
        ),
        expected_output=(
            "qa_report.md written via Write Output File. "
            "Returns SENTINEL_PASS or SENTINEL_BLOCK with exit code and error details."
        ),
        agent=qa_agent,
        context=context or [],
    )
