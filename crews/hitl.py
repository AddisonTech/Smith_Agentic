"""
crews/hitl.py
Human-in-the-loop plan approval helper.

Usage (inside any crew builder):
    from crews.hitl import approve_plan

    approved_goal = approve_plan(goal, orchestrator, llm, cfg)
    # then proceed to build the full crew with approved_goal
"""
from __future__ import annotations

from crewai import Agent, Crew, LLM, Process, Task


def approve_plan(goal: str, orchestrator: Agent, llm: LLM, config: dict) -> str:
    """
    Run the Orchestrator alone to produce an execution plan, show it to the
    user, and loop until the user approves or provides revisions.

    Returns the final goal string (enriched with approved plan notes).

    If config['crew']['hitl'] is False, skips approval and returns goal unchanged.
    """
    if not config.get("crew", {}).get("hitl", True):
        return goal

    print("\n" + "=" * 60)
    print("  HUMAN-IN-THE-LOOP: Plan Approval")
    print("=" * 60)
    print(f"  Goal: {goal}")
    print("  Generating execution plan...\n")

    iteration = 0
    current_goal = goal

    while True:
        iteration += 1
        plan_task = Task(
            description=(
                f"Goal: {current_goal}\n\n"
                "Produce a detailed, numbered execution plan for accomplishing this goal. "
                "Include: what to research, what to build, what to validate, and the order of operations. "
                "Be specific about deliverables and success criteria."
            ),
            expected_output=(
                "A numbered execution plan with clear steps, each step specifying: "
                "what agent handles it, what inputs they need, and what output they produce."
            ),
            agent=orchestrator,
        )

        mini_crew = Crew(
            agents=[orchestrator],
            tasks=[plan_task],
            process=Process.sequential,
            verbose=False,
        )
        plan_result = mini_crew.kickoff()

        print("\n" + "-" * 60)
        print(f"  PROPOSED PLAN (iteration {iteration}):")
        print("-" * 60)
        print(plan_result)
        print("-" * 60)

        decision = input(
            "\n  [A]pprove and continue  /  type revision notes: "
        ).strip()

        if decision.lower() in ("a", "approve", "y", "yes", ""):
            print("\n  Plan approved. Launching full crew...\n")
            # Enrich goal with approved plan as context
            return (
                f"{current_goal}\n\n"
                f"[Approved Execution Plan]\n{plan_result}"
            )
        else:
            print(f"\n  Revision requested: {decision}")
            print("  Regenerating plan with your notes...\n")
            current_goal = f"{goal}\n\n[Human revision notes]: {decision}"
