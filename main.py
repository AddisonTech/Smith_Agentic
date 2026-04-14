"""
main.py — SmithAgentic entrypoint.

Usage:
    python main.py --goal "Write a technical spec for a REST API rate limiter"
    python main.py --goal "..." --model qwen2.5:14b
    python main.py --goal "..." --model mistral:7b --no-verbose
    python main.py --goal "..." --crew plc
    python main.py --goal "..." --crew react
    python main.py --goal "..." --no-hitl

Run from inside smith_agentic/:
    cd smith_agentic
    python main.py --goal "..."

Or from the parent directory:
    python smith_agentic/main.py --goal "..."

Web UI:
    python smith_agentic/ui/server.py
    then open http://localhost:8765
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure smith_agentic/ is on sys.path regardless of where the script is invoked from.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config.loader import load_config, get_crew_model
from crews.default_crew import build_crew as build_default_crew
from crews.plc_crew import build_crew as build_plc_crew
from crews.react_crew import build_crew as build_react_crew
from crews.vision_crew import build_crew as build_vision_crew


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SmithAgentic — multi-agent CrewAI system powered by local Ollama models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py --goal "Explain the CAP theorem with code examples"
  python main.py --goal "Write a production-ready Python logging module" --model qwen2.5:14b
  python main.py --goal "Design a caching strategy for a high-traffic API" --no-verbose
  python main.py --goal "Build a Rockwell PLC program for a conveyor system" --crew plc
  python main.py --goal "Build a React dashboard for machine status" --crew react
  python main.py --goal "Run a Vision_Inspect defect analysis and report" --crew vision
        """,
    )
    parser.add_argument(
        "--goal", "-g",
        required=True,
        metavar="GOAL",
        help="The high-level goal for the crew to accomplish.",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        metavar="MODEL",
        help=(
            "Override the Ollama model. Must match a tag from `ollama list`. "
            "Examples: llama3.1:8b, qwen2.5:14b, mistral:7b, deepseek-r1:8b. "
            "Defaults to the model set in config/config.yaml."
        ),
    )
    parser.add_argument(
        "--crew", "-c",
        default="default",
        metavar="CREW",
        help="Which crew to run: 'default', 'plc', 'react', 'vision'. (default: default)",
    )
    parser.add_argument(
        "--no-verbose",
        action="store_true",
        default=False,
        help="Suppress per-agent verbose output. Shows only final results.",
    )
    parser.add_argument(
        "--no-hitl",
        action="store_true",
        default=False,
        help="Skip human-in-the-loop plan approval. Run fully autonomously.",
    )
    return parser.parse_args()


# ── Entry ─────────────────────────────────────────────────────────────────────

_CREW_BUILDERS = {
    "default": build_default_crew,
    "plc":     build_plc_crew,
    "react":   build_react_crew,
    "vision":  build_vision_crew,
}


def main() -> None:
    args = _parse_args()
    cfg  = load_config()

    # CLI --model overrides the per-crew default for this run only.
    # Store in _model_override so crew builders can detect it cleanly.
    if args.model:
        cfg["_model_override"] = args.model
    if args.no_verbose:
        cfg["crew"]["verbose"] = False

    hitl = not args.no_hitl
    cfg["crew"]["hitl"] = hitl

    _banner(args, cfg)

    if args.crew not in _CREW_BUILDERS:
        print(f"[ERROR] Unknown crew: '{args.crew}'. Supported: {', '.join(_CREW_BUILDERS)}.")
        sys.exit(1)

    crew   = _CREW_BUILDERS[args.crew](goal=args.goal, config=cfg)
    result = crew.kickoff()

    print(f"\n{'='*60}")
    print("  FINAL OUTPUT")
    print(f"{'='*60}\n")
    print(result)
    print(f"\n{'='*60}")
    print("  Check outputs/ for all saved files.")
    print(f"{'='*60}\n")


def _banner(args: argparse.Namespace, cfg: dict) -> None:
    sep = "=" * 60
    effective_model = cfg.get("_model_override") or get_crew_model(cfg, args.crew)
    print(f"\n{sep}")
    print("  SmithAgentic — Multi-Agent Crew")
    print(sep)
    print(f"  Model  : {effective_model}")
    print(f"  Crew   : {args.crew}")
    print(f"  Verbose: {cfg['crew'].get('verbose', True)}")
    print(f"  HITL   : {cfg['crew'].get('hitl', True)}")
    print(f"  Goal   : {args.goal}")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
