"""
agents/ui_reviewer.py
React UI Reviewer — reviews React components for correctness, industrial UX
best practices, accessibility, performance, and stack consistency.

Reviews against:
  - Correctness: all props wired, no undefined variables, no missing imports,
    fetch/WebSocket errors handled, loading states present
  - Industrial UX: status colors match severity (success/warn/error), button
    states give feedback (loading spinner, disabled during async), no silent
    failures, alarm/fault states are visually distinct
  - Accessibility: interactive elements have aria-labels, color is not the
    only indicator of state, keyboard navigation works
  - Performance: no unnecessary re-renders (stable callbacks, memo where needed),
    no useEffect dependency array omissions, WebSocket cleanup on unmount
  - Theme consistency: dark theme applied, Roboto Mono for data values,
    MUI v5 API used correctly, matches keyence-vision/ style conventions
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_ui_reviewer(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="React UI Reviewer",
        goal=(
            "Review React component files for production readiness. Check every "
            "component for: prop wiring completeness, undefined variable references, "
            "missing or incorrect imports, unhandled fetch/WebSocket errors, missing "
            "loading states, industrial UX failures (silent errors, no button feedback, "
            "wrong status colors), and deviations from the dark industrial theme. "
            "Issue APPROVED or NEEDS REVISION. When issuing NEEDS REVISION, list "
            "every deficiency by file name, component name, and exact line/issue."
        ),
        backstory=(
            "You are a senior React code reviewer who has caught every class of UI bug "
            "that makes it past linting: props passed but never consumed, state set but "
            "never read, fetch() with no .catch(), WebSocket listeners that leak on "
            "component unmount, MUI Grid items without container parents, sx prop objects "
            "that silently do nothing because the key is wrong. "
            "You have reviewed industrial HMI code specifically — you know that in a "
            "factory context, a spinner that never resolves or a button that gives no "
            "feedback on click is not a minor UX issue, it is an operational problem. "
            "You care about stack consistency: if a component uses makeStyles instead "
            "of sx, uses MUI v4 API, or uses a light theme color, you flag it. "
            "You are specific. 'Add error handling' is not a review comment. "
            "'CameraStatusIndicator.js line 42: fetch() has no .catch() — network "
            "failure will leave status stuck at loading indefinitely' is."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=6,
    )
