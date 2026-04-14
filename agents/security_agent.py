"""
agents/security_agent.py
Security Reviewer agent — OWASP Top-10 code audit.
Issues SECURITY_BLOCK, SECURITY_PASS_WITH_WARNINGS, or SECURITY_PASS.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_security_agent(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Security Reviewer",
        goal=(
            "Review all generated code for OWASP Top-10 vulnerabilities, hardcoded secrets, "
            "injection risks, and unsafe subprocess usage. Read the deliverable using "
            "Read Output File. Write a security report to 'security_report.md'. "
            "If critical issues are found (hardcoded credentials, shell injection, arbitrary "
            "code execution), issue verdict SECURITY_BLOCK. "
            "For warnings only, issue SECURITY_PASS_WITH_WARNINGS. "
            "For clean code, issue SECURITY_PASS."
        ),
        backstory=(
            "You are an application security engineer with deep expertise in OWASP Top 10, "
            "Python security patterns, and code audit. You read every line, not summaries. "
            "You catch hardcoded tokens, injection points, and dangerous eval/exec usage. "
            "Your reports list each finding by category, severity (CRITICAL/HIGH/MEDIUM/LOW), "
            "and exact line reference. You never pass code with critical findings."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=6,
    )
