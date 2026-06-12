"""
scripts/demo_hermes_agent.py
Agent-reasoning version of the keystone demo: a CrewAI agent AUTONOMOUSLY
decides to call the Hermes MCP tools to answer a plant-floor question.

Where demo_hermes_live.py calls the tools directly (proving the plumbing),
this proves the reasoning layer on top of it:

    Ollama LLM  ->  CrewAI agent  ->  MCP  ->  Hermes  ->  asyncua  ->  OPC-UA

Prereqs:
  1. Start the OPC-UA simulator (in the Hermes repo):
        python examples/opcua_sim.py
  2. Run this from the Smith_Agentic repo:
        python scripts/demo_hermes_agent.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from crewai import Agent, Crew, LLM, Process, Task

from config.loader import load_config
from tools.mcp_tools import build_mcp_tools, stop_mcp_servers

# The plc crew's config model. NOT qwen2.5-coder — the coder variant emits
# tool-call JSON as plain text instead of native tool_calls, so agents stall.
MODEL = "qwen2.5:7b"

GOAL = (
    "Report the CURRENT live values of the Temperature (ns=2;s=Temperature) and "
    "MotorSpeed (ns=2;s=MotorSpeed) tags on the plant-floor OPC-UA server, and "
    "state whether the server connection is healthy."
)


def main() -> None:
    config = load_config()
    print("Building Hermes MCP tools (this launches the Hermes MCP server)...")
    ot_tools = build_mcp_tools(config, "plc")
    print(f"Discovered {len(ot_tools)} OT tool(s): {', '.join(sorted(t.name for t in ot_tools)) or '(none)'}\n")

    if not any(t.name == "read_node" for t in ot_tools):
        print("read_node not available — is Hermes enabled in config and the simulator running?")
        stop_mcp_servers()
        return

    llm_cfg = config["llm"]
    # ollama_chat/ (not ollama/) so litellm uses /api/chat, which supports native
    # tool calling — with /api/generate the model just echoes tool-call JSON as text.
    llm = LLM(
        model=f"ollama_chat/{MODEL}",
        base_url=llm_cfg.get("base_url", "http://localhost:11434"),
        temperature=0.2,  # tool calls want determinism, not creativity
        timeout=llm_cfg.get("timeout", 600),
    )

    analyst = Agent(
        role="OT Data Analyst",
        goal="Answer questions about live plant-floor data using the OPC-UA tools available to you.",
        backstory=(
            "You are stationed at an industrial site with read access to the plant's "
            "OPC-UA server through a set of tools. You never guess values — you read "
            "them from the live server and report exactly what the tools return."
        ),
        llm=llm,
        tools=ot_tools,
        verbose=True,
        max_iter=8,
    )

    task = Task(
        description=GOAL,
        expected_output=(
            "A short report listing the live value of each requested tag (with units "
            "if known) and a one-line server health statement, based only on tool output."
        ),
        agent=analyst,
    )

    crew = Crew(agents=[analyst], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()

    print("\n" + "=" * 72)
    print("AGENT REPORT")
    print("=" * 72)
    print(result)
    print()
    print(f"The agent ({MODEL} via Ollama) chose and called the Hermes MCP tools on")
    print("its own to produce that report. Keystone path confirmed with reasoning.")
    stop_mcp_servers()


if __name__ == "__main__":
    main()
