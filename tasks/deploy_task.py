"""
tasks/deploy_task.py
Deployment validation task — Deployment Validator checks artifacts are deployable.
"""
from __future__ import annotations

from crewai import Agent, Task


def create_deploy_task(
    deploy_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Validate deployment readiness for this goal:\n\n"
            f"  GOAL: {goal}\n\n"
            "Step 1: Use 'Read Output File' to read deliverable_revised.md "
            "(fall back to deliverable.md if the revised version does not exist).\n"
            "Step 2: For each Python code block in the deliverable:\n"
            "  - Extract the code block\n"
            "  - Run it via 'Execute Python Code' using this compile-check script:\n"
            "      import py_compile, tempfile, os\n"
            "      code = '''PASTE_CODE_HERE'''\n"
            "      with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:\n"
            "          f.write(code); fname = f.name\n"
            "      py_compile.compile(fname, doraise=True)\n"
            "      os.unlink(fname)\n"
            "      print('Compile OK')\n"
            "  - A CompileError = DEPLOY_BLOCKED\n"
            "Step 3: Use 'Write Output File' to write deploy_report.md with:\n"
            "  - VERDICT: DEPLOY_READY or DEPLOY_BLOCKED\n"
            "  - Numbered list of blocking issues (or 'None' if clean)\n"
            "  - SUMMARY: overall deployment readiness assessment\n\n"
            "Do not give your final answer until deploy_report.md has been written."
        ),
        expected_output=(
            "deploy_report.md written via Write Output File with VERDICT "
            "(DEPLOY_READY or DEPLOY_BLOCKED) and a list of any blocking issues."
        ),
        agent=deploy_agent,
        context=context or [],
    )
