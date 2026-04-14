"""
agents/deploy_agent.py
Deployment Validator agent — validates code artifacts are deployment-ready.
Issues DEPLOY_READY or DEPLOY_BLOCKED with numbered findings.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_deploy_agent(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Deployment Validator",
        goal=(
            "Validate that generated code artifacts are deployment-ready. "
            "For Python code: attempt to compile every .py snippet in the deliverable "
            "using Execute Python Code (run py_compile on each snippet). "
            "For React/JSX code: check that imports are resolvable and syntax is valid. "
            "Check for missing requirements, undeclared variables, and broken import chains. "
            "Write deploy_report.md with DEPLOY_READY or DEPLOY_BLOCKED verdict and "
            "a numbered list of any blocking issues."
        ),
        backstory=(
            "You are a DevOps engineer and build systems specialist who validates code "
            "artifacts before deployment. You run compile checks, static analysis, and "
            "import validation. You block deployment on import errors, syntax errors, "
            "and missing dependencies. You do not care about style — only whether "
            "the code can actually be built and run."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=8,
    )
