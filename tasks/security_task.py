"""
tasks/security_task.py
Security review task — Security Reviewer audits the deliverable for OWASP Top-10.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_security_task(
    security_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Review all generated code for security vulnerabilities. Goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use 'Read Output File' to read deliverable_revised.md "
            "(fall back to deliverable.md if the revised version does not exist).\n"
            "Step 2: Check for each of the following:\n"
            "  - Hardcoded secrets, tokens, passwords, or API keys\n"
            "  - Shell injection (subprocess called with shell=True on user input)\n"
            "  - Path traversal (unvalidated file paths from user input)\n"
            "  - Unsafe deserialization (pickle or yaml.load on untrusted data)\n"
            "  - eval() or exec() called on user-controlled input\n"
            "  - Missing input validation at system boundaries\n"
            "Step 3: Use 'Write Output File' to write security_report.md with:\n"
            "  - VERDICT: SECURITY_BLOCK, SECURITY_PASS_WITH_WARNINGS, or SECURITY_PASS\n"
            "  - Numbered list of findings (category, severity, description)\n"
            "  - SUMMARY: overall security posture assessment\n\n"
            "Do not give your final answer until security_report.md has been written."
        ),
        expected_output=(
            "security_report.md written via Write Output File with VERDICT "
            "(SECURITY_BLOCK / SECURITY_PASS_WITH_WARNINGS / SECURITY_PASS) "
            "and a numbered findings list."
        ),
        agent=security_agent,
        context=context or [],
    )
