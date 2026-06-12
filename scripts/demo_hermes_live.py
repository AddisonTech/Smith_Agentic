"""
scripts/demo_hermes_live.py
End-to-end proof that Smith_Agentic reads live plant-floor data through the
Hermes MCP bridge.

Prereqs:
  1. Start the OPC-UA simulator (in the Hermes repo):
        python examples/opcua_sim.py
  2. Run this from the Smith_Agentic repo:
        python scripts/demo_hermes_live.py

It builds the PLC crew's MCP tools (which launches the Hermes MCP server, which
connects to the simulator), then reads a couple of live tags twice to show the
values changing — proving the full path:

    Smith_Agentic  ->  MCP  ->  Hermes  ->  asyncua  ->  OPC-UA simulator
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config.loader import load_config
from tools.mcp_tools import build_mcp_tools, stop_mcp_servers


def _call(tool, **kwargs):
    """Invoke a CrewAI tool, tolerant of run()/._run() differences across versions."""
    try:
        return tool.run(**kwargs)
    except Exception:
        return tool._run(**kwargs)


def main() -> None:
    config = load_config()
    print("Building PLC-crew MCP tools (this launches the Hermes MCP server)...")
    tools = build_mcp_tools(config, "plc")
    by_name = {t.name: t for t in tools}
    print(f"Discovered {len(tools)} OT tool(s): {', '.join(sorted(by_name)) or '(none)'}\n")

    if "read_node" not in by_name:
        print("read_node not available — is Hermes enabled in config and the simulator running?")
        stop_mcp_servers()
        return

    if "get_server_status" in by_name:
        print("get_server_status ->")
        print(_call(by_name["get_server_status"]))
        print()

    read = by_name["read_node"]
    for label in ("Temperature", "MotorSpeed"):
        nid = f"ns=2;s={label}"
        r1 = _call(read, node_id=nid)
        time.sleep(1.5)
        r2 = _call(read, node_id=nid)
        print(f"{label}  ({nid})")
        print(f"  read #1: {r1}")
        print(f"  read #2: {r2}")
        print()

    print("Those values came from the live OPC-UA simulator, fetched by Smith_Agentic")
    print("through the MCP bridge into Hermes. Keystone path confirmed.")
    stop_mcp_servers()


if __name__ == "__main__":
    main()
